import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Union, MutableMapping

from flask import current_app
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Query, joinedload, defaultload
from sqlalchemy.orm.collections import (
    attribute_mapped_collection,
)
from sqlalchemy.orm.strategy_options import loader_option

from timApp.answer.answer import Answer
from timApp.answer.answer_models import UserAnswer
from timApp.auth.accesstype import AccessType
from timApp.auth.auth_models import BlockAccess
from timApp.auth.get_user_rights_for_item import UserItemRights
from timApp.auth.session.model import UserSession
from timApp.document.docinfo import DocInfo
from timApp.document.timjsonencoder import TimJsonEncoder
from timApp.folder.createopts import FolderCreationOptions
from timApp.folder.folder import Folder
from timApp.item.block import Block
from timApp.item.item import ItemBase
from timApp.lecture.lectureusers import LectureUsers
from timApp.messaging.messagelist.listinfo import Channel
from timApp.messaging.timMessage.internalmessage_models import (
    InternalMessageReadReceipt,
)
from timApp.notification.notification import Notification, NotificationType
from timApp.sisu.scimusergroup import ScimUserGroup
from timApp.timdb.exceptions import TimDbException
from timApp.timdb.sqa import db, TimeStampMixin, is_attribute_loaded
from timApp.user.hakaorganization import HakaOrganization, get_home_organization_id
from timApp.user.personaluniquecode import SchacPersonalUniqueCode, PersonalUniqueCode
from timApp.user.preferences import Preferences
from timApp.user.scimentity import SCIMEntity
from timApp.user.special_group_names import (
    ANONYMOUS_GROUPNAME,
    ANONYMOUS_USERNAME,
    LOGGED_IN_GROUPNAME,
    SPECIAL_USERNAMES,
)
from timApp.user.usercontact import (
    UserContact,
    PrimaryContact,
    ContactOrigin,
    NO_AUTO_VERIFY_ORIGINS,
)
from timApp.user.usergroup import (
    UserGroup,
    get_logged_in_group_id,
    get_anonymous_group_id,
)
from timApp.user.usergroupmember import (
    UserGroupMember,
    membership_current,
    membership_deleted,
)
from timApp.user.userutils import (
    grant_access,
    get_access_type_id,
    create_password_hash,
    check_password_hash,
    check_password_hash_old,
)
from timApp.util.utils import (
    remove_path_special_chars,
    cached_property,
    get_current_time,
)

ItemOrBlock = Union[ItemBase, Block]
maxdate = datetime.max.replace(tzinfo=timezone.utc)

view_access_set = {
    t.value
    for t in [
        AccessType.view,
        AccessType.copy,
        AccessType.edit,
        AccessType.owner,
        AccessType.teacher,
        AccessType.see_answers,
        AccessType.manage,
    ]
}

edit_access_set = {
    t.value
    for t in [
        AccessType.edit,
        AccessType.owner,
        AccessType.manage,
    ]
}

manage_access_set = {
    t.value
    for t in [
        AccessType.owner,
        AccessType.manage,
    ]
}

owner_access_set = {
    t.value
    for t in [
        AccessType.owner,
    ]
}

teacher_access_set = {
    t.value
    for t in [
        AccessType.owner,
        AccessType.manage,
        AccessType.teacher,
    ]
}

seeanswers_access_set = {
    t.value
    for t in [
        AccessType.owner,
        AccessType.teacher,
        AccessType.see_answers,
        AccessType.manage,
    ]
}

copy_access_set = {
    t.value
    for t in [
        AccessType.copy,
        AccessType.edit,
        AccessType.owner,
        AccessType.manage,
    ]
}

access_sets = {
    AccessType.copy: copy_access_set,
    AccessType.edit: edit_access_set,
    AccessType.manage: manage_access_set,
    AccessType.owner: owner_access_set,
    AccessType.see_answers: seeanswers_access_set,
    AccessType.teacher: teacher_access_set,
    AccessType.view: view_access_set,
}

SCIM_USER_NAME = ":scimuser"


class Consent(Enum):
    CookieOnly = 1
    CookieAndData = 2


class UserOrigin(Enum):
    """Indicates how the user originally registered to TIM.

    Only Email, Korppi and Sisu are used so far; the others are speculative.
    """

    Email = 1
    Korppi = 2
    Sisu = 3
    Haka = 4
    OpenID = 5
    OpenIDConnect = 6
    Facebook = 7
    Google = 8
    Twitter = 9

    def to_contact_origin(self):
        if self == UserOrigin.Email:
            return ContactOrigin.Custom
        elif self == UserOrigin.Korppi or self == UserOrigin.Haka:
            return ContactOrigin.Haka
        elif self == UserOrigin.Sisu:
            return ContactOrigin.Sisu
        return ContactOrigin.Custom


@dataclass
class UserInfo:
    username: str | None = None
    email: str | None = None
    full_name: str | None = None
    given_name: str | None = None
    last_name: str | None = None
    origin: UserOrigin | None = None
    password: str | None = None
    password_hash: str | None = None
    unique_codes: list[SchacPersonalUniqueCode] = field(default_factory=list)

    def __post_init__(self):
        assert (
            self.password is None or self.password_hash is None
        ), "Cannot pass both password and password_hash to UserInfo"


def last_name_to_first(full_name: str | None):
    """Converts a name of the form "Firstname Middlenames Lastname" to "Lastname Firstname Middlenames"."""
    if full_name is None:
        return None
    names = full_name.split(" ")
    if len(names) > 1:
        return f'{names[-1]} {" ".join(names[:-1])}'
    return full_name


def last_name_to_last(full_name: str | None):
    """Converts a name of the form "Lastname Firstname Middlenames" to "Firstname Middlenames Lastname"."""
    if full_name is None:
        return None
    names = full_name.split(" ")
    if len(names) > 1:
        return f'{" ".join(names[1:])} {names[0]}'
    return full_name


deleted_user_suffix = "_deleted"
deleted_user_pattern = re.compile(rf".*{deleted_user_suffix}(_\d+)?$")


def user_query_with_joined_groups() -> Query:
    return User.query.options(joinedload(User.groups))


class User(db.Model, TimeStampMixin, SCIMEntity):
    """A user account. Used to identify users.

    .. note:: Some user IDs are reserved for internal use:

              * ID `0` is used to denote all "Anonymous users"
    """

    __tablename__ = "useraccount"
    id = db.Column(db.Integer, primary_key=True)
    """User identifier."""

    name = db.Column(db.Text, nullable=False, unique=True)
    """User name (not full name). Used to identify the user and during log-in."""

    given_name = db.Column(db.Text)
    """User's given name."""

    last_name = db.Column(db.Text)
    """User's last name."""

    real_name = db.Column(db.Text)
    """Real (full) name. This may be in the form "Lastname Firstname" or "Firstname Lastname"."""

    _email = db.Column("email", db.Text, unique=True)
    """Email address."""

    prefs = db.Column(db.Text)
    """Preferences as a JSON string."""

    pass_ = db.Column("pass", db.Text)
    """Password hashed with bcrypt."""

    consent = db.Column(db.Enum(Consent), nullable=True)
    """Current consent for cookie/data collection."""

    origin = db.Column(db.Enum(UserOrigin), nullable=True)
    """How the user registered to TIM."""

    uniquecodes = db.relationship(
        "PersonalUniqueCode",
        back_populates="user",
        collection_class=attribute_mapped_collection("user_collection_key"),
    )
    """Personal unique codes used to identify the user via Haka Identity Provider."""

    internalmessage_readreceipt: InternalMessageReadReceipt | None = db.relationship(
        "InternalMessageReadReceipt", back_populates="user"
    )
    """User's read receipts for internal messages."""

    primary_email_contact = db.relationship(
        UserContact,
        primaryjoin=(id == UserContact.user_id)
        & (UserContact.primary == PrimaryContact.true)
        & (UserContact.channel == Channel.EMAIL),
        lazy="select",
        uselist=False,
    )
    """
    The primary email contact for the user.
    
    The primary contact is the preferred email address that the user wants to receive notifications from TIM.
    """

    def _get_email(self) -> str:
        return self._email

    def _set_email(self, value: str) -> None:
        self.update_email(value)

    # Decorators don't work with mypy yet
    # See https://github.com/dropbox/sqlalchemy-stubs/issues/98
    email = hybrid_property(_get_email, _set_email)
    """
    User's primary email address.
    
    This is the address the user can log in with and receive notifications from TIM.
    """

    consents = db.relationship("ConsentChange", back_populates="user", lazy="select")
    """User's consent changes."""

    contacts: list[UserContact] = db.relationship(
        "UserContact", back_populates="user", lazy="select"
    )
    """User's contacts."""

    notifications = db.relationship(
        "Notification", back_populates="user", lazy="dynamic"
    )
    """Notification settings for the user. Represents what notifications the user wants to receive."""

    groups: list[UserGroup] = db.relationship(
        UserGroup,
        UserGroupMember.__table__,
        primaryjoin=(id == UserGroupMember.user_id) & membership_current,
        back_populates="users",
        lazy="select",
    )
    """Current groups of the user is a member of."""

    groups_dyn = db.relationship(
        UserGroup,
        UserGroupMember.__table__,
        primaryjoin=id == UserGroupMember.user_id,
        lazy="dynamic",
    )
    """All groups of the user as a dynamic query."""

    groups_inactive = db.relationship(
        UserGroup,
        UserGroupMember.__table__,
        primaryjoin=(id == UserGroupMember.user_id) & membership_deleted,
        lazy="dynamic",
    )
    """All groups the user is no longer a member of as a dynamic query."""

    memberships_dyn = db.relationship(
        UserGroupMember,
        foreign_keys="UserGroupMember.user_id",
        lazy="dynamic",
    )
    """User's group memberships as a dynamic query."""

    memberships: list[UserGroupMember] = db.relationship(
        UserGroupMember,
        foreign_keys="UserGroupMember.user_id",
    )
    """All user's group memberships."""

    active_memberships = db.relationship(
        UserGroupMember,
        primaryjoin=(id == UserGroupMember.user_id) & membership_current,
        collection_class=attribute_mapped_collection("UserGroupMember.usergroup_id"),
        # back_populates="group",
    )
    """Active group memberships mapped by user group ID."""

    lectures = db.relationship(
        "Lecture",
        secondary=LectureUsers.__table__,
        back_populates="users",
        lazy="select",
    )
    """Lectures that the user is attending at the moment."""

    owned_lectures = db.relationship("Lecture", back_populates="owner", lazy="dynamic")
    """Lectures that the user has created."""

    lectureanswers = db.relationship(
        "LectureAnswer", back_populates="user", lazy="dynamic"
    )
    """Lecture answers that the user sent to lectures as a dynamic query."""

    messages = db.relationship("Message", back_populates="user", lazy="dynamic")
    """Lecture messages that the user sent to lectures as a dynamic query."""

    questionactivity = db.relationship(
        "QuestionActivity", back_populates="user", lazy="select"
    )
    """User's activity on lecture questions."""

    useractivity = db.relationship("Useractivity", back_populates="user", lazy="select")
    """User's activity during lectures."""

    answers = db.relationship(
        "Answer", secondary=UserAnswer.__table__, back_populates="users", lazy="dynamic"
    )
    """User's answers to tasks as a dynamic query."""

    annotations = db.relationship(
        "Annotation", back_populates="annotator", lazy="dynamic"
    )
    """User's task annotations as a dynamic query."""

    velps = db.relationship("Velp", back_populates="creator", lazy="dynamic")
    """Velps created by the user as a dynamic query."""

    sessions: list[UserSession] = db.relationship(
        "UserSession", back_populates="user", lazy="select"
    )
    """All user's sessions as a dynamic query."""

    active_sessions: MutableMapping[str, UserSession] = db.relationship(
        "UserSession",
        primaryjoin=(id == UserSession.user_id) & ~UserSession.expired,
        collection_class=attribute_mapped_collection("session_id"),
    )
    """Active sessions mapped by the session ID."""

    # Used for copying
    notifications_alt = db.relationship("Notification")
    owned_lectures_alt = db.relationship("Lecture")
    lectureanswers_alt = db.relationship("LectureAnswer")
    messages_alt = db.relationship("Message")
    answers_alt = db.relationship("Answer", secondary=UserAnswer.__table__)
    annotations_alt = db.relationship("Annotation")
    velps_alt = db.relationship("Velp")

    def update_email(
        self,
        new_email: str,
        create_contact: bool = True,
        notify_message_lists: bool = True,
    ):
        """
        Updates the user's primary email address.

        .. note:: Prefer setting :attr:`email` instead of using this method. For example:

                    >>> user = User.get_by_name("testuser1")
                    >>> user.email = "newemail@example.com"
                    >>> db.session.commit()
                    None

        :param new_email: New email address.
        :param create_contact: Whether to create a new contact for the new email address. Defaults to `True`.
                                If `False`, updates only the user's email address info without updating the primary contact.
        :param notify_message_lists: If `True`, send a notification to all message lists that the user is subscribed to.
                                     Defaults to `True`.
        """
        from timApp.messaging.messagelist.emaillist import update_mailing_list_address

        prev_email = self._email
        self._email = new_email
        if prev_email != new_email:
            if create_contact:
                new_primary = UserContact.query.filter_by(
                    user_id=self.id, channel=Channel.EMAIL, contact=new_email
                ).first()
                if not new_primary:
                    # If new primary contact does not exist for the email, create it
                    # This is used mainly for CLI operations where email of the user is changed directly
                    new_primary = UserContact(
                        user=self,
                        verified=True,
                        channel=Channel.EMAIL,
                        contact=new_email,
                        contact_origin=ContactOrigin.Custom,
                    )
                    db.session.add(new_primary)
                self.primary_email_contact.primary = None
                new_primary.primary = PrimaryContact.true

            if notify_message_lists:
                update_mailing_list_address(prev_email, new_email)

    @property
    def scim_display_name(self):
        """User's display name in format used by SCIM API."""
        return last_name_to_last(self.real_name)

    @property
    def scim_created(self):
        """User's creation date in format used by SCIM API."""
        return self.created

    @property
    def scim_modified(self):
        """User's last modification date in format used by SCIM API."""
        return self.modified

    @property
    def scim_id(self):
        """User's identifier in format used by SCIM API."""
        return self.name

    @property
    def scim_resource_type(self):
        """The resource type of the user in format used by SCIM API."""
        return "User"

    @property
    def scim_extra_data(self):
        """Any extra data that should be returned in the SCIM API response."""
        email_contacts = UserContact.query.filter_by(
            user=self, channel=Channel.EMAIL, verified=True
        )
        return {"emails": [{"value": uc.contact} for uc in email_contacts]}

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email}, real_name={self.real_name})>"

    @property
    def logged_in(self):
        return self.id > 0

    @property
    def is_deleted(self) -> bool:
        return (self.email and deleted_user_pattern.match(self.email) is not None) or (
            self.name and deleted_user_pattern.match(self.name) is not None
        )

    @property
    def group_ids(self):
        return {g.id for g in self.groups}

    @cached_property
    def is_admin(self):
        for g in self.groups:
            if g.name == "Administrators":
                return True
        return False

    @property
    def is_email_user(self):
        """Returns whether the user signed up via email and has not been "upgraded" to Korppi or Sisu user."""
        return "@" in self.name or self.name.startswith("testuser")

    @property
    def pretty_full_name(self):
        """Returns the user's full name."""
        if self.is_name_hidden:
            return f"User {self.id}"
        if self.given_name and self.last_name:
            return f"{self.given_name} {self.last_name}"
        if self.real_name is None:
            return "(real_name is null)"
        parts = self.real_name.split(" ")
        if len(parts) == 1:
            return self.real_name
        return " ".join(parts[1:]) + " " + parts[0]

    @staticmethod
    def create_with_group(
        info: UserInfo,
        is_admin: bool = False,
        uid: int | None = None,
    ) -> tuple["User", UserGroup]:
        p_hash = (
            create_password_hash(info.password)
            if info.password is not None
            else info.password_hash
        )
        user = User(
            id=uid,
            name=info.username,
            real_name=info.full_name,
            last_name=info.last_name,
            given_name=info.given_name,
            _email=info.email,
            pass_=p_hash,
            origin=info.origin,
        )
        if info.email:
            primary_email = UserContact(
                contact=info.email,
                contact_origin=info.origin.to_contact_origin()
                if info.origin
                else ContactOrigin.Custom,
                verified=True,
                primary=PrimaryContact.true,
                channel=Channel.EMAIL,
            )
            user.contacts.append(primary_email)
            # Mark the email also primary for possible checks within the same session
            user.primary_email_contact = primary_email
        db.session.add(user)
        user.set_unique_codes(info.unique_codes)
        group = UserGroup.create(info.username)
        user.groups.append(group)
        if is_admin:
            user.make_admin()
        return user, group

    @staticmethod
    def get_by_name(name: str) -> Optional["User"]:
        return user_query_with_joined_groups().filter_by(name=name).first()

    @staticmethod
    def get_by_id(uid: int) -> Optional["User"]:
        return user_query_with_joined_groups().get(uid)

    @staticmethod
    def get_by_email(email: str) -> Optional["User"]:
        if email is None:
            raise Exception("Tried to find an user by null email")
        return user_query_with_joined_groups().filter_by(email=email).first()

    @staticmethod
    def get_by_email_case_insensitive(email: str) -> list["User"]:
        return (
            user_query_with_joined_groups()
            .filter(func.lower(User.email).in_([email]))
            .all()
        )

    @staticmethod
    def get_by_email_case_insensitive_or_username(
        email_or_username: str,
    ) -> list["User"]:
        users = User.get_by_email_case_insensitive(email_or_username)
        if users:
            return users
        u = User.get_by_name(email_or_username)
        if u:
            return [u]
        return []

    @property
    def verified_email_name_parts(self) -> list[str]:
        email_parts = [
            uc.contact.split("@")
            for uc in UserContact.query.filter_by(
                user=self, channel=Channel.EMAIL, verified=True
            )
        ]
        return [parts[0].lower() for parts in email_parts]

    @property
    def is_special(self):
        return self.name in SPECIAL_USERNAMES

    # Used by authlib mixins (e.g. authlib.integrations.sqla_oauth2.create_save_token_func)
    def get_user_id(self):
        return self.id

    def check_password(
        self, password: str, allow_old=False, update_if_old=True
    ) -> bool:
        if not self.pass_:
            return False
        is_ok = check_password_hash(password, self.pass_)
        if is_ok:
            return True
        if not allow_old:
            return False
        is_ok = check_password_hash_old(password, self.pass_)
        if is_ok and update_if_old:
            self.pass_ = create_password_hash(password)
        return is_ok

    def make_admin(self):
        ag = UserGroup.get_admin_group()
        if ag not in self.groups:
            self.groups.append(ag)

    def get_home_org_student_id(self):
        home_org_id = get_home_organization_id()
        puc = self.uniquecodes.get((home_org_id, "studentID"), None)
        return puc.code if puc is not None else None

    def get_personal_group(self) -> UserGroup:
        return self.personal_group_prop

    @cached_property
    def personal_group_prop(self) -> UserGroup:
        group_to_find = self.name
        if self.name == ANONYMOUS_USERNAME:
            group_to_find = ANONYMOUS_GROUPNAME
        for g in self.groups:
            if g.name == group_to_find:
                return g
        raise TimDbException(f"Personal usergroup for user {self.name} was not found!")

    def derive_personal_folder_name(self):
        real_name = self.real_name
        if not real_name:
            real_name = "anonymous"
        basename = remove_path_special_chars(real_name).lower()
        index = ""
        while Folder.find_by_path("users/" + basename + index):
            index = str(int(index or 1) + 1)
        return basename + index

    def get_personal_folder(self) -> Folder:
        return self.personal_folder_prop

    @cached_property
    def personal_folder_prop(self) -> Folder:
        if self.logged_in:
            group_condition = UserGroup.name == self.name
        else:
            group_condition = UserGroup.name == ANONYMOUS_GROUPNAME
        folders: list[Folder] = (
            Folder.query.join(BlockAccess, BlockAccess.block_id == Folder.id)
            .join(UserGroup, UserGroup.id == BlockAccess.usergroup_id)
            .filter(
                (Folder.location == "users")
                & group_condition
                & (BlockAccess.type == AccessType.owner.value)
            )
            .with_entities(Folder)
            .options(
                defaultload(Folder._block)
                .joinedload(Block.accesses)
                .joinedload(BlockAccess.usergroup)
            )
            .all()
        )
        if len(folders) >= 2:
            raise TimDbException(
                f"Found multiple personal folders for user {self.name}: {[f.name for f in folders]}"
            )
        if not folders:
            f = Folder.create(
                "users/" + self.derive_personal_folder_name(),
                self.get_personal_group(),
                title=f"{self.real_name}",
                creation_opts=FolderCreationOptions(apply_default_rights=True),
            )
            db.session.commit()
            return f
        return folders[0]

    def get_prefs(self) -> Preferences:
        prefs = json.loads(self.prefs or "{}")
        try:
            return Preferences.from_json(prefs)
        except TypeError:
            return Preferences()

    def set_prefs(self, prefs: Preferences):
        self.prefs = json.dumps(prefs, cls=TimJsonEncoder)

    def get_groups(
        self, include_special: bool = True, include_expired: bool = True
    ) -> Query:
        special_groups = [ANONYMOUS_GROUPNAME]
        if self.logged_in:
            special_groups.append(LOGGED_IN_GROUPNAME)
        filter_expr = UserGroupMember.user_id == self.id
        if not include_expired:
            filter_expr = filter_expr & membership_current
        q = UserGroup.query.filter(
            UserGroup.id.in_(
                db.session.query(UserGroupMember.usergroup_id).filter(filter_expr)
            )
        )
        if include_special:
            q = q.union(UserGroup.query.filter(UserGroup.name.in_(special_groups)))
        return q

    def add_to_group(
        self,
        ug: UserGroup,
        added_by: Optional["User"],
        sync_mailing_lists=True,
    ) -> bool:
        """
        Adds the user to a group.

        :param ug: The user group to add the user to.
        :param added_by: Optionally, the user that added this user to the group.
        :param sync_mailing_lists: If True, automatically notifies message lists about the added user.
        :return: True, if the added user is a "new" member (i.e. never was a member of the group before).
        """
        # Avoid cyclical importing.
        from timApp.messaging.messagelist.messagelist_utils import (
            sync_message_list_on_add,
        )

        existing: UserGroupMember = (
            self.id is not None and self.memberships_dyn.filter_by(group=ug).first()
        )
        if existing:
            if existing.membership_end is not None:
                existing.membership_added = get_current_time()
                existing.adder = added_by
            existing.membership_end = None
            new_add = False
        else:
            self.memberships.append(UserGroupMember(group=ug, adder=added_by))
            new_add = True
        # On changing of group, sync this person to the user group's message lists.
        if sync_mailing_lists:
            sync_message_list_on_add(self, ug)
        return new_add

    def get_contact(
        self,
        channel: Channel,
        contact: str,
        options: list[loader_option] | None = None,
    ) -> UserContact | None:
        """Find user's contact by channel and contact contents.

        :param channel: Contact channel.
        :param contact: Contact contents.
        :param options: Additional DB load options.
        :return: UserContact if found, otherwise None.
        """
        q = UserContact.query.filter(
            (UserContact.user == self)
            & (UserContact.channel == channel)
            & (UserContact.contact == contact)
        )
        if options:
            q = q.options(*options)
        return q.first()

    @staticmethod
    def get_scimuser() -> "User":
        u = User.get_by_name(SCIM_USER_NAME)
        if not u:
            u, _ = User.create_with_group(
                UserInfo(
                    username=SCIM_USER_NAME,
                    full_name="Scim User",
                    email="scimuser@example.com",
                )
            )
        return u

    @staticmethod
    def get_anon() -> "User":
        return User.get_by_id(0)

    def update_info(self, info: UserInfo, sync_mailing_lists: bool = True) -> None:
        if info.username and self.name != info.username:
            group = self.get_personal_group()
            self.name = info.username
            group.name = info.username
        if info.given_name:
            self.given_name = info.given_name
        if info.last_name:
            self.last_name = info.last_name
        if info.full_name:
            self.real_name = info.full_name
        if info.email:
            email_origin = (
                info.origin.to_contact_origin() if info.origin else ContactOrigin.Custom
            )
            self.set_emails(
                [info.email],
                email_origin,
                force_verify=True,
                force_primary=True,
                remove=False,
                notify_message_lists=sync_mailing_lists,
            )
        if info.password:
            self.pass_ = create_password_hash(info.password)
        elif info.password_hash:
            self.pass_ = info.password_hash
        self.set_unique_codes(info.unique_codes)

    def set_emails(
        self,
        emails: list[str],
        origin: ContactOrigin,
        force_verify: bool = False,
        force_primary: bool = False,
        can_update_primary: bool = False,
        add: bool = True,
        remove: bool = True,
        notify_message_lists: bool = True,
    ) -> None:
        """Sets emails for the given origin.

        Existing emails for the given origin are overwritten.
        If the user's primary email is removed,
        it is changed to the next verified email of the same origin.

        :param emails: List of emails to set to the given origin.
        :param origin: Emails' origin
        :param force_verify: If True, all emails are marked as verified.
                             Otherwise, origins in NO_AUTO_VERIFY_ORIGINS are not verified.
        :param force_primary: If True, forces to update the primary address
        :param can_update_primary: If True, allows to "update" the primary email address.
                                If the user's primary email is custom and a new email is added from the integration,
                                set that email as primary.
                                Also, if user's primary email is custom and a new email is added is also custom,
                                set the first email address in the list as primary.
        :param add: If True, adds new emails in the list to the user.
        :param remove: If True, removes emails not present in emails list.
        :param notify_message_lists: If True, notifies the message lists about the change.
        """

        if not emails:
            return

        with db.session.no_autoflush:
            # Get emails for the current origin
            # We use self.contacts for now because the only contacts we save are email contacts and because it allows
            # to call this method multiple times within the same transaction
            current_email_contacts = [
                uc
                for uc in self.contacts
                if uc.channel == Channel.EMAIL and uc.contact_origin == origin
            ]
            current_email_dict: dict[str, UserContact] = {
                uc.contact: uc for uc in current_email_contacts
            }

            new_emails = set(emails)
            current_emails = {uc.contact for uc in current_email_contacts}

            to_add = new_emails - current_emails if add else set()
            to_remove = current_emails - new_emails if remove else set()
            not_removed = set() if remove else current_emails - new_emails
            new_email_contacts: dict[str, UserContact] = {
                email: current_email_dict[email]
                for email in ((new_emails & current_emails) | not_removed)
            }

            change_primary_email = force_primary or (
                self.primary_email_contact is None
                or (
                    self.primary_email_contact.contact_origin == origin
                    and self.primary_email_contact.contact in to_remove
                )
                or (origin == ContactOrigin.Custom and can_update_primary)
            )

            if to_add:
                verified = force_verify or origin not in NO_AUTO_VERIFY_ORIGINS
                # Resolve all emails to add that don't belong to the current origin
                added_email_contacts = [
                    uc
                    for uc in self.contacts
                    if uc.channel == Channel.EMAIL
                    and uc.contact_origin != origin
                    and uc.contact in to_add
                ]
                added_email_contacts_set = {uc.contact for uc in added_email_contacts}
                other_origin_email_contacts: dict[str, UserContact] = {
                    uc.contact: uc for uc in added_email_contacts
                }

                # If this is a new integration and actual new emails are added (and not just updated),
                # we can update the primary email
                change_primary_email = change_primary_email or (
                    can_update_primary
                    and origin != ContactOrigin.Custom
                    and not current_email_contacts
                    and len(to_add - added_email_contacts_set) > 0
                )

                for email in to_add:
                    # If the email is already registered to the user, adjust its origin
                    if email in other_origin_email_contacts:
                        uc = other_origin_email_contacts[email]
                        uc.contact_origin = origin
                    else:
                        uc = UserContact(
                            channel=Channel.EMAIL,
                            verified=verified,
                            contact_origin=origin,
                            contact=email,
                        )
                        self.contacts.append(uc)
                    new_email_contacts[email] = uc

            for email in to_remove:
                uc = current_email_dict[email]
                db.session.delete(uc)
                self.contacts.remove(uc)

            if change_primary_email:
                # Ensure no email is primary
                if self.primary_email_contact:
                    self.primary_email_contact.primary = None

                if emails:
                    new_primary = new_email_contacts[emails[0]]
                elif new_email_contacts:
                    new_primary = next(uc for uc in new_email_contacts.values())
                else:
                    new_primary = next(
                        (uc for uc in self.contacts if uc.channel == Channel.EMAIL),
                        None,
                    )

                    if not new_primary:
                        # Special case: this update operation ends up deleting all emails of the user
                        # This is not desired in most cases, so we will have to adjust by taking
                        # one of the deleted emails and re-adding it as a Custom email
                        new_primary = UserContact(
                            user=self,
                            contact_origin=ContactOrigin.Custom,
                            verified=True,
                            contact=next(u for u in current_email_contacts).contact,
                        )
                        self.contacts.append(new_primary)

                new_primary.primary = PrimaryContact.true
                self.update_email(
                    new_primary.contact,
                    create_contact=False,
                    notify_message_lists=notify_message_lists,
                )

    def set_unique_codes(self, codes: list[SchacPersonalUniqueCode]):
        for c in codes:
            ho = HakaOrganization.get_or_create(name=c.org)
            if ho.id is None or self.id is None:
                db.session.flush()
            puc = PersonalUniqueCode(
                code=c.code,
                type=c.codetype,
                org_id=ho.id,
            )
            if puc.user_collection_key not in self.uniquecodes:
                self.uniquecodes[puc.user_collection_key] = puc

    def has_some_access(
        self,
        i: ItemOrBlock,
        vals: set[int],
        allow_admin: bool = True,
        grace_period: timedelta = timedelta(seconds=0),
        duration: bool = False,
    ) -> BlockAccess | None:
        """
            Check if the user has any possible access to the given item or block.

        :param i: The item or block to check
        :param vals: Access types to check. See AccessType for available values.
        :param allow_admin: If True, allow admins to bypass the access check
        :param grace_period: Grace period for the access check.
                             If the user has access to the item, extends the end date of the access by this amount.
        :param duration: If True checks for duration access instead of active accesses.
        :return: The best access object that user currently has for the given item or block and access types.
        """
        if allow_admin and self.is_admin:
            return BlockAccess(
                block_id=i.id,
                accessible_from=datetime.min.replace(tzinfo=timezone.utc),
                type=AccessType.owner.value,
                usergroup_id=self.get_personal_group().id,
            )

        from timApp.auth.session.util import has_valid_session

        if not has_valid_session(self):
            return None

        if isinstance(i, ItemBase):
            b = i.block
        else:
            b = i
        if not b:
            return None
        now = get_current_time()
        best_access = None
        curr_group_ids = self.group_ids
        for a in b.accesses.values():  # type: BlockAccess
            if a.usergroup_id not in curr_group_ids:
                if self.logged_in and a.usergroup_id == get_logged_in_group_id():
                    pass
                elif a.usergroup_id == get_anonymous_group_id():
                    pass
                else:
                    continue
            if a.type not in vals:
                continue
            to_time = a.accessible_to
            if to_time is not None:
                to_time += grace_period
            if (a.accessible_from or maxdate) <= now < (to_time or maxdate):
                # If the end time of the access is unrestricted, there is no better access.
                if to_time is None:
                    return a
                # If the end time of the access is restricted, there might be a better access,
                # so we'll continue looping.
                if best_access is None or best_access.accessible_to < a.accessible_to:
                    best_access = a
            if (
                duration
                and a.unlockable
                and ((a.duration_from or maxdate) <= now < (a.duration_to or maxdate))
            ):
                return a
        return best_access

    def has_access(
        self,
        i: ItemOrBlock,
        access: AccessType,
        grace_period: timedelta = timedelta(seconds=0),
        duration: bool = False,
    ) -> BlockAccess | None:
        """
            Check if the user has access to the given item or block.

        :param i: Item or block to check
        :param access: Access type to check. See AccessType for available values.
        :param grace_period: Grace period for the access check.
                             If the user has access to the item, extends the end date of the access by this amount.
        :param duration: If True checks for duration access instead of active accesses.
        :return: The best access object that user currently has for the given item or block and access type.
                 Otherwise, if user has no access, None.
        """
        from timApp.auth.accesshelper import check_inherited_right

        return check_inherited_right(
            self, i, access, grace_period
        ) or self.has_some_access(
            i, access_sets[access], grace_period=grace_period, duration=duration
        )

    def has_view_access(
        self, i: ItemOrBlock, duration: bool = False
    ) -> BlockAccess | None:
        return self.has_some_access(i, view_access_set, duration=duration)

    def has_edit_access(
        self, i: ItemOrBlock, duration: bool = False
    ) -> BlockAccess | None:
        return self.has_some_access(i, edit_access_set, duration=duration)

    def has_manage_access(
        self, i: ItemOrBlock, duration: bool = False
    ) -> BlockAccess | None:
        return self.has_some_access(i, manage_access_set, duration=duration)

    def has_teacher_access(
        self, i: ItemOrBlock, duration: bool = False
    ) -> BlockAccess | None:
        return self.has_some_access(i, teacher_access_set, duration=duration)

    def has_seeanswers_access(
        self, i: ItemOrBlock, duration: bool = False
    ) -> BlockAccess | None:
        return self.has_some_access(i, seeanswers_access_set, duration=duration)

    def has_copy_access(
        self, i: ItemOrBlock, duration: bool = False
    ) -> BlockAccess | None:
        return self.has_some_access(i, copy_access_set, duration=duration)

    def has_ownership(
        self, i: ItemOrBlock, allow_admin: bool = True
    ) -> BlockAccess | None:
        return self.has_some_access(i, owner_access_set, allow_admin)

    def can_write_to_folder(self, f: Folder):
        # not even admins are allowed to create new items in 'users' folder
        if f.path == "users":
            return False
        return self.has_edit_access(f)

    def grant_access(
        self,
        block: ItemOrBlock,
        access_type: AccessType,
        accessible_from: datetime | None = None,
        accessible_to: datetime | None = None,
        duration_from: datetime | None = None,
        duration_to: datetime | None = None,
        duration: timedelta | None = None,
        require_confirm: bool | None = None,
    ):
        return grant_access(
            group=self.get_personal_group(),
            block=block,
            access_type=access_type,
            accessible_from=accessible_from,
            accessible_to=accessible_to,
            duration_from=duration_from,
            duration_to=duration_to,
            duration=duration,
            require_confirm=require_confirm,
        )

    def remove_access(self, block_id: int, access_type: str):
        BlockAccess.query.filter_by(
            block_id=block_id,
            usergroup_id=self.get_personal_group().id,
            type=get_access_type_id(access_type),
        ).delete()

    def get_notify_settings(self, item: DocInfo | Folder) -> dict:
        # TODO: Instead of conversion, expose all notification types in UI
        n: list[Notification] = self.notifications.filter_by(block_id=item.id).all()

        result = {
            "email_doc_modify": False,
            "email_comment_add": False,
            "email_comment_modify": False,
            "email_answer_add": False,
        }

        for nn in n:
            if nn.notification_type in (
                NotificationType.DocModified,
                NotificationType.ParAdded,
                NotificationType.ParDeleted,
                NotificationType.ParModified,
            ):
                result["email_doc_modify"] = True
            if nn.notification_type in (NotificationType.CommentAdded,):
                result["email_comment_add"] = True
            if nn.notification_type in (
                NotificationType.CommentModified,
                NotificationType.CommentDeleted,
            ):
                result["email_comment_modify"] = True
            if nn.notification_type in (NotificationType.AnswerAdded,):
                result["email_answer_add"] = True

        return result

    def set_notify_settings(
        self,
        item: DocInfo | Folder,
        doc_modify: bool,
        comment_add: bool,
        comment_modify: bool,
        answer_add: bool,
    ):
        # TODO: Instead of conversion, expose all notification types in UI
        notification_types = []
        if doc_modify:
            notification_types.extend(
                (
                    NotificationType.DocModified,
                    NotificationType.ParAdded,
                    NotificationType.ParDeleted,
                    NotificationType.ParModified,
                )
            )
        if comment_add:
            notification_types.extend((NotificationType.CommentAdded,))
        if comment_modify:
            notification_types.extend(
                (
                    NotificationType.CommentModified,
                    NotificationType.CommentDeleted,
                )
            )
        if answer_add:
            notification_types.extend((NotificationType.AnswerAdded,))

        self.notifications.filter((Notification.block_id == item.id)).delete(
            synchronize_session=False
        )
        for nt in notification_types:
            db.session.add(
                Notification(
                    user=self,
                    block_id=item.id,
                    notification_type=nt,
                )
            )

    def get_answers_for_task(self, task_id: str):
        return (
            self.answers.options(joinedload(Answer.users_all))
            .order_by(Answer.id.desc())
            .filter_by(task_id=task_id)
        )

    @property
    def is_name_hidden(self):
        return getattr(self, "hide_name", False)

    @property
    def is_sisu_teacher(self) -> bool:
        """Whether the user belongs to at least one Sisu teacher group"""
        if self.is_special:
            return False
        teacher_group_id = (
            db.session.query(ScimUserGroup.group_id)
            .join(UserGroup)
            .join(UserGroupMember)
            .filter(
                (UserGroupMember.user_id == self.id)
                & ScimUserGroup.external_id.like("%-teachers")
            )
            .first()
        )
        return teacher_group_id is not None

    @property
    def basic_info_dict(self):
        if not self.is_name_hidden:
            info_dict = {
                "id": self.id,
                "name": self.name,
                "real_name": self.real_name,
                "email": self.email,
            }
        else:
            info_dict = {
                "id": self.id,
                "name": f"user{self.id}",
                "real_name": f"User {self.id}",
                "email": f"user{self.id}@example.com",
            }

        if is_attribute_loaded("uniquecodes", self):
            info_dict["student_id"] = self.get_home_org_student_id()

        return info_dict

    def to_json(self, full: bool = False, contacts: bool = False) -> dict:
        external_ids: dict[int, str] = (
            {
                s.group_id: s.external_id
                for s in ScimUserGroup.query.filter(
                    ScimUserGroup.group_id.in_([g.id for g in self.groups])
                ).all()
            }
            if full
            else []
        )

        result = self.basic_info_dict

        if full:
            result |= {
                "group": self.get_personal_group(),
                "groups": [
                    {**g.to_json(), "external_id": external_ids.get(g.id, None)}
                    for g in self.groups
                ],
                "folder": self.get_personal_folder() if self.logged_in else None,
                "consent": self.consent,
                "last_name": self.last_name,
            }

        if contacts:
            result |= {"contacts": self.contacts}

        return result

    @cached_property
    def bookmarks(self):
        from timApp.bookmark.bookmarks import Bookmarks

        return Bookmarks(self)

    def belongs_to_any_of(self, *groups: UserGroup):
        return bool(set(groups) & set(self.groups))

    @staticmethod
    def get_model_answer_user() -> Optional["User"]:
        # TODO: think other languages also
        return User.get_by_name(current_app.config["MODEL_ANSWER_USER_NAME"])


def get_membership_end(u: User, group_ids: set[int]) -> datetime | None:
    """
    Get the end of the membership of the user in the given groups.

    .. note:: If the user's membership ended in multiple groups, the latest end date is returned.

    :param u: The user
    :param group_ids: The IDs of the groups
    :return: The end of the membership or
             None if the user is not a member of the groups or if the user's membership hasn't ended yet
    """

    relevant_memberships: list[UserGroupMember] = [
        m for m in u.memberships if m.usergroup_id in group_ids
    ]
    membership_end = None
    # If the user is not active in any of the groups, we'll show the lastly-ended membership.
    # TODO: It might be possible in the future that the membership_end is in the future.
    if relevant_memberships and all(
        m.membership_end is not None for m in relevant_memberships
    ):
        membership_end = max(m.membership_end for m in relevant_memberships)
    return membership_end


def get_membership_added(u: User, group_ids: set[int]) -> datetime | None:
    """
    Get the earliest time the user was added to the given groups.

    :param u: The user
    :param group_ids: The IDs of the groups
    :return: The earliest time the user was added to the given groups
             or None if the user is not a member of the groups
    """

    relevant_memberships: list[UserGroupMember] = [
        m for m in u.memberships if m.usergroup_id in group_ids
    ]
    membership_added_times = [
        m.membership_added
        for m in relevant_memberships
        if m.membership_added is not None
    ]
    return min(membership_added_times) if membership_added_times else None


def has_no_higher_right(access_type: str | None, rights: UserItemRights) -> bool:
    """
    Checks whether the given access type (view, edit, ...) has no higher match in the given UserItemRights.
    For example, if rights has {'edit': True}, then has_no_higher_right('view', rights) is False.
    For now, only works for view, edit, see_answers and teacher access types.

    :param access_type The access type to check.
    :param rights The UserItemRights to consider.
    :return True if access_type is one of view, edit, see_answers or teacher and there is no higher right in the
     UserItemRights, False otherwise.
    """
    if not access_type:
        return False
    return {
        "view": not rights["editable"] and not rights["see_answers"],
        "edit": not rights["see_answers"],
        "see_answers": not rights["teacher"],
        "teacher": not rights["manage"],
    }.get(access_type, False)


def get_owned_objects_query(u: User):
    return (
        u.get_personal_group()
        .accesses.filter_by(type=AccessType.owner.value)
        .with_entities(BlockAccess.block_id)
    )
