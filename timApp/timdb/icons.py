from contracts import contract
from timdb.timdbbase import TimDbBase,TimDbException


class Icons(TimDbBase):
    @contract
    def __init__(self, db_path: 'Connection', files_root_path: 'str', type_name: 'str', current_user_name: 'str'):
        """Initializes TimDB with the specified database and root path.

        :param type_name: The type name.
        :param current_user_name: The name of the current user.
        :param db_path: The path of the database file.
        :param files_root_path: The root path where all the files will be stored.
        """
        TimDbBase.__init__(self, db_path, files_root_path, type_name, current_user_name)

    @contract
    def get_file_name(self,icon_id: 'int') -> 'str':
        """Retrieves the filename for the icon.

        :param icon_id: The id of the icon.
        :return: A filename for the icon.
        """
        cursor=self.db.cursor()
        cursor.execute('SELECT filename FROM Icon WHERE id=?',icon_id)
        results=cursor.fetchall()
        if not results:
            raise TimDbException('No icon with id '+icon_id+' found.')
        filename=results.pop()
        return filename