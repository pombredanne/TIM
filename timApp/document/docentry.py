from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING, Any, Dict

from sqlalchemy.orm import foreign

from timApp.document.docinfo import DocInfo
from timApp.document.document import Document
from timApp.document.translation.translation import Translation
from timApp.folder.createopts import FolderCreationOptions
from timApp.item.block import BlockType
from timApp.item.block import insert_block
from timApp.timdb.exceptions import ItemAlreadyExistsException
from timApp.timdb.sqa import db
from timApp.user.usergroup import UserGroup
from timApp.util.utils import split_location

if TYPE_CHECKING:
    from timApp.user.user import User


class DocEntry(db.Model, DocInfo):
    """Represents a TIM document in the directory hierarchy.

    A document can have several aliases, which is why the primary key is "name" column and not "id".

    Most of the time you should use DocInfo class instead of this.
    """
    __tablename__ = 'docentry'
    name = db.Column(db.Text, primary_key=True)
    """Full path of the document.
    
    TODO: Improve the name.
    """

    id = db.Column(db.Integer, db.ForeignKey('block.id'), nullable=False)
    """Document identifier."""

    public = db.Column(db.Boolean, nullable=False, default=True)
    """Whether the document is visible in directory listing."""

    _block = db.relationship('Block', back_populates='docentries', lazy='joined')

    trs: List[Translation] = db.relationship(
        'Translation',
        primaryjoin=id == foreign(Translation.src_docid),
        back_populates='docentry',
    )

    __table_args__ = (db.Index('docentry_id_idx', 'id'),)

    @property
    def tr(self) -> Optional[Translation]:
        return next((tr for tr in self.trs if tr.doc_id == self.id), None)

    @property
    def path(self) -> str:
        return self.name

    @property
    def path_without_lang(self) -> str:
        return self.name

    @property
    def lang_id(self) -> Optional[str]:
        return self.tr.lang_id if self.tr else None

    # noinspection PyMethodOverriding
    @lang_id.setter
    def lang_id(self, value: str) -> None:
        tr = self.tr
        if tr:
            tr.lang_id = value
        else:
            # noinspection PyArgumentList
            self.trs.append(Translation(src_docid=self.id, lang_id=value, doc_id=self.id))

    @property
    def translations(self) -> List['Translation']:
        trs = self.trs
        if not self.tr:
            self.trs.append(Translation(src_docid=self.id, doc_id=self.id, lang_id=''))
        return trs

    @staticmethod
    def get_all() -> List['DocEntry']:
        return DocEntry.query.all()

    @staticmethod
    def find_all_by_id(doc_id: int) -> List['DocEntry']:
        return DocEntry.query.filter_by(id=doc_id).all()

    @staticmethod
    def find_by_id(doc_id: int, docentry_load_opts: Any=None) -> Optional['DocInfo']:
        """Finds a DocInfo by id.

        TODO: This method doesn't really belong in DocEntry class.
        """
        q = DocEntry.query.filter_by(id=doc_id)
        if docentry_load_opts:
            q = q.options(*docentry_load_opts)
        d = q.first()
        if d:
            return d
        return Translation.query.get(doc_id)

    @staticmethod
    def find_by_path(
            path: str,
            fallback_to_id: bool = False,
            try_translation: bool = True,
            docentry_load_opts: Any = None
    ) -> Optional['DocInfo']:
        """Finds a DocInfo by path, falling back to id if specified.

        TODO: This method doesn't really belong in DocEntry class.
        """
        if docentry_load_opts is None:
            docentry_load_opts = []
        d = DocEntry.query.options(*docentry_load_opts).get(path)
        if d:
            return d
        # try translation
        if try_translation:
            base_doc_path, lang = split_location(path)
            entry = DocEntry.find_by_path(base_doc_path, try_translation=False, docentry_load_opts=docentry_load_opts)
            if entry is not None:
                tr = Translation.query.filter_by(src_docid=entry.id, lang_id=lang).first()
                if tr is not None:
                    tr.docentry = entry
                    return tr
        if fallback_to_id:
            try:
                return DocEntry.find_by_id(int(path), docentry_load_opts=docentry_load_opts)
            except ValueError:
                return None
        return d

    @staticmethod
    def get_dummy(title: str) -> 'DocEntry':
        # noinspection PyArgumentList
        return DocEntry(id=-1, name=title)

    @staticmethod
    def create(path: str,
               owner_group: Optional[UserGroup] = None,
               title: Optional[str] = None,
               from_file: Optional[str]=None,
               initial_par: Optional[str]=None,
               settings: Optional[Dict]=None,
               folder_opts: FolderCreationOptions=FolderCreationOptions()) -> 'DocEntry':
        """Creates a new document with the specified properties.

        :param from_file: If provided, loads the document content from a file.
        :param initial_par: The initial paragraph for the document.
        :param settings: The settings for the document.
        :param title: The document title.
        :param path: The path of the document to be created (can be None). If None, no DocEntry is actually added
         to the database; only Block and Document objects are created.
        :param owner_group: The owner group.
        :param folder_opts: Options for creating intermediate folders.
        :returns: The newly created document object.

        """

        location, _ = split_location(path)
        from timApp.folder.folder import Folder
        Folder.create(location, owner_groups=owner_group, creation_opts=folder_opts)

        document = create_document_and_block(owner_group, title or path)

        # noinspection PyArgumentList
        docentry = DocEntry(id=document.doc_id, name=path, public=True)
        docentry._doc = document
        if path is not None:
            if Folder.find_by_path(path):
                db.session.rollback()
                raise ItemAlreadyExistsException(f'A folder already exists at path {path}')
            db.session.add(docentry)

        if from_file is not None:
            with open(from_file, encoding='utf-8') as f:
                document.add_text(f.read())
        elif initial_par is not None:
            document.add_text(initial_par)
        if settings is not None:
            document.set_settings(settings)

        return docentry


def create_document_and_block(owner_group: Optional[UserGroup], desc: Optional[str] = None) -> Document:
    block = insert_block(BlockType.Document, desc, [owner_group] if owner_group else None)
    # Must flush because we need to know the document id in order to create the document in the filesystem.
    db.session.flush()
    document_id = block.id
    document = Document(document_id, modifier_group_id=owner_group.id if owner_group else UserGroup.get_admin_group().id)
    document.create()
    return document


def get_documents(include_nonpublic: bool = False,
                  filter_folder: Optional[str] = None,
                  search_recursively: bool = True,
                  filter_user: Optional[User] = None,
                  custom_filter: Any=None,
                  query_options: Any=None) -> List[DocEntry]:
    """Gets all the documents in the database matching the given criteria.

    :param filter_user: If specified, returns only the documents that the user has view access to.
    :param search_recursively: Whether to search recursively.
    :param filter_folder: Optionally restricts the search to a specific folder.
    :param include_nonpublic: Whether to include non-public document names or not.
    :param custom_filter: Any custom filter to use.
    :param query_options: Any additional options for the query.
    :returns: A list of DocEntry objects.

    """

    q = DocEntry.query
    if not include_nonpublic:
        q = q.filter_by(public=True)
    if filter_folder is not None:
        filter_folder = filter_folder.strip('/') + '/'
        if filter_folder == '/':
            filter_folder = ''
        q = q.filter(DocEntry.name.like(filter_folder + '%'))
        if not search_recursively:
            q = q.filter(DocEntry.name.notlike(filter_folder + '%/%'))
    if custom_filter is not None:
        q = q.filter(custom_filter)
    if query_options is not None:
        q = q.options(query_options)
    result = q.all()
    if not filter_user:
        return result
    return [r for r in result if filter_user.has_view_access(r)]


def get_documents_in_folder(folder_pathname: str,
                            include_nonpublic: bool = False) -> List[DocEntry]:
    """Gets all the documents in a folder.

    :param folder_pathname: path to be searched for documents without ending '/'
    :param include_nonpublic: Whether to include non-public document names or not.
    :returns: A list of DocEntry objects.

    """
    return get_documents(include_nonpublic=include_nonpublic,
                         filter_folder=folder_pathname,
                         search_recursively=False)
