import copy
from sqlite3 import Connection
from typing import Optional, List, Dict
from timdb.timdbbase import TimDbBase, TimDbException
from assessment_area import AssessmentArea, assessment_area_from_document


class Velps(TimDbBase):
    """
    Used as an interface to query the database about velps.
    """

    def __init__(self, db_path: Connection, files_root_path: str, type_name: str, current_user_name: str):
        """Initializes TimDB with the specified database and root path.

        :param type_name: The type name.
        :param current_user_name: The name of the current user.
        :param db_path: The path of the database file.
        :param files_root_path: The root path where all the files will be stored.
        """
        TimDbBase.__init__(self, db_path, files_root_path, type_name, current_user_name)

    def create_new_velp(self, creator_id: int, content=str, default_points: Optional[float] = None,
                        icon_id: Optional[int] = None, valid_until: Optional[str] = None,
                        language_id: str = "FI") -> int:
        """Creates a new velp with all information

        Creates a new velp with all necessary information in one function using three others
        :param creator_id: User ID of creator.
        :param content: Text for velp.
        :param default_points: Default points for velp, None if not given.
        :param icon_id: Icon ID attached to velp. Can be null.
        :param valid_until: Time after velp becomes unusable.
        :param language_id: Language ID of velp.
        :return: id of the new velp.
        """
        new_velp_id = self._create_velp(creator_id, default_points, icon_id, valid_until)
        new_version_id = self.create_velp_version(new_velp_id)
        self.create_velp_content(new_version_id, language_id, content)
        return new_velp_id

    def _create_velp(self, creator_id: int, default_points: Optional[float], icon_id: Optional[int] = None,
                     valid_until: Optional[str] = None):
        """Creates a new entry to the velp table.

        :param creator_id: User ID of creator.
        :param default_points: Default points for velp.
        :param icon_id: Icon ID attached to velp. Can be null.
        :param valid_until: Time after velp becomes unusable.
        :return: ID of velp that was just created
        """
        cursor = self.db.cursor()
        cursor.execute("""
                      INSERT INTO
                      Velp(creator_id, default_points, icon_id, valid_until)
                      VALUES(?, ?, ?, ?)
                      """, [creator_id, default_points, icon_id, valid_until]
                       )
        self.db.commit()
        velp_id = cursor.lastrowid
        return velp_id

    def create_velp_version(self, velp_id: int):
        """Creates a new version for a velp to use

        :param velp_id: ID of velp we're adding version for
        :return: ID of version that was just created
        """
        cursor = self.db.cursor()
        cursor.execute("""
                      INSERT INTO
                      VelpVersion(velp_id)
                      VALUES(?)
                      """, [velp_id]
                       )
        self.db.commit()
        version_id = cursor.lastrowid
        return version_id

    def create_velp_content(self, version_id: int, language_id: str, content: str):
        """Method to create content (text) for velp

        :param version_id: Version ID where the content will be stored
        :param language_id: Language id
        :param content: Text of velp
        :return: -
        """
        cursor = self.db.cursor()
        cursor.execute("""
                      INSERT INTO
                      VelpContent(version_id, language_id, content)
                      VALUES (?, ?, ?)
                      """, [version_id, language_id, content]
                       )
        self.db.commit()

    def update_velp(self, velp_id: int, new_content: str, languages: str):
        """Updates velp content

        :param velp_id: ID of velp that's being updated
        :param new_content: New velp text
        :param languages: Language used
        :return:
        """
        cursor = self.db.cursor()
        cursor.execute("""
        """)
        cursor.execute("""
                      INSERT INTO
                      VelpVersion(velp_id)
                      VALUES (?)
                      """, [velp_id]
                       )
        new_versionId = cursor.lastrowid
        cursor.execute("""
                      INSERT INTO
                      VelpContent(version_id, language_id, content)
                      VALUES (?, ?, ?)
                      """, [new_versionId, languages[0], new_content[0]]
                       )

    def check_velp_languages(self, velp_id: int):
        """Fetches all languages used within one velp

        :param velp_id: Velp ID
        :return: Returns languages as JSON
        """
        cursor = self.db.cursor()
        cursor.execute("""
                      SELECT
                      language_id
                      FROM
                      VelpInformation
                      WHERE id = ?
                      """, [velp_id]
                       )
        results = self.resultAsDictionary(cursor)  # e.g. [{'language_id': 'EN'}, {'language_id': 'FI'}]
        return results

    def get_latest_velp_version(self, velp_id: int, language_id: str = "FI"):
        """Method to fetch the latest version for velp in specific language

        :param velp_id: ID of velp we're checking
        :param language_id: ID of language
        :return: ID of version
        """
        cursor = self.db.cursor()
        cursor.execute("""
                      SELECT
                      MAX(id)
                      FROM
                      VelpInformation
                      WHERE velp_id = ? AND language_id = ?
                      """, [velp_id, language_id]
                       )
        velp_version = cursor.fetchone()[0]
        return velp_version

    def get_velps(self, assessment_area: AssessmentArea, language_id: str = 'FI') -> List[Dict]:
        """Get velps that are linked to an assessment area.

        :param assessment_area: the relevant assessment area
        :param language_id The id of the language. 'EN', for example.
        :return: A list of dictionaries, each describing a different velp.
        """

        cursor = self.db.cursor()
        cursor.execute("""
                       SELECT Velp.id AS id, Velp.default_points AS points, Velp.icon_id AS icon_id,
                       y.content AS content, y.language_id AS language_id
                       FROM Velp
                       INNER JOIN(
                         SELECT x.velp_id, VelpContent.content, VelpContent.language_id
                         FROM VelpContent
                         INNER JOIN (
                           SELECT VelpVersion.velp_id, max(VelpVersion.id) AS latest_version
                           FROM VelpVersion GROUP BY VelpVersion.velp_id
                           ) AS x ON VelpContent.version_id = x.latest_version
                       ) AS y ON y.velp_id = velp.id
                       WHERE y.language_id = ? AND velp_id IN (
                       """ +
                       assessment_area.get_sql_for_velp_ids()
                       + """
                       )
                       """, [language_id] + assessment_area.get_parameters_for_velp_ids()
                       )
        results = self.resultAsDictionary(cursor)
        return results

    def get_document_velps(self, doc_id: int, language_id: str = 'FI') -> List[Dict]:
        """Gets velps that are linked to the document. Also gets labels for the velps.

        :param doc_id: The id of the document.
        :param language_id The id of the language. 'EN', for example.
        :return: A list of dictionaries, each describing a different velp.
        """
        assessment_area = assessment_area_from_document(doc_id)
        velp_data = self.get_velps(assessment_area, language_id)
        label_data = self.get_velp_label_ids(assessment_area)

        if velp_data and label_data:  # Do magic with labels if data exists
            velp_id = label_data[0]['velp_id']
            list_help = []
            label_dict = {}
            for i in range(len(label_data)):
                next_id = label_data[i]['velp_id']
                if next_id != velp_id:
                    label_dict[velp_id] = copy.deepcopy(list_help)
                    velp_id = next_id
                    del list_help[:]
                    list_help.append(label_data[i]['labels'])
                else:
                    list_help.append(label_data[i]['labels'])
                if i == len(label_data) - 1:
                    label_dict[velp_id] = copy.deepcopy(list_help)
            for i in range(len(velp_data)):
                searchID = velp_data[i]['id']
                if searchID in label_dict:
                    velp_data[i]['labels'] = label_dict[searchID]
        return velp_data

    def create_label(self, language_id: str, content: str) -> int:
        """
        Creates a new label
        :param language_id: Language chosen
        :param content: Label content
        :return: id of the new label
        """
        cursor = self.db.cursor()
        cursor.execute("""
                      INSERT INTO
                      Label(language_id, content, id)
                      VALUES (?, ?, (SELECT
                      MAX(Label.id)+1
                      FROM Label))
                      """, [language_id, content]
                       )
        self.db.commit()
        label_id = cursor.lastrowid
        return label_id

    def add_label_translation(self, label_id: int, language_id: str, content: str):
        """
        Adds new translation to an existing label
        :param label_id: Label id
        :param language_id: Language chosen
        :param content: New translation
        """
        cursor = self.db.cursor()
        cursor.execute("""
                      INSERT INTO
                      Label(id, language_id, content)
                      VALUES (?, ?, ?)
                      """, [label_id, language_id, content]
                       )
        self.db.commit()

    def update_label(self, label_id: int, language_id: str, content: str):
        """
        Updates content of label in specific language
        :param label_id: Label id
        :param language_id: Language chosen
        :param content: Updated content
        :return:
        """
        cursor = self.db.cursor()
        cursor.execute("""
                      UPDATE Label
                      SET content = ?
                      WHERE id = ? AND language_id = ?
                      """, [content, label_id, language_id]
                       )
        self.db.commit()

    def get_velp_label_ids(self, velp_id: int):
        """
        Gets information of labels for one velp in specific language
        :param velp_id: ID of velp
        :return: List of labels associated with the velp
        """
        cursor = self.db.cursor()
        cursor.execute("""
                      SELECT LabelInVelp.label_id
                      FROM LabelInVelp
                      WHERE LabelInVelp.velp_id = ?
                      """, [velp_id]
                       )
        return self.resultAsDictionary(cursor)

    def add_labels_to_velp(self, velp_id: int, labels: List[int]):
        """Associates a set of labels to a velp. (Appends to existing labels)

        :param velp_id: id of the velp that
        :param labels: list of label ids.
        :return: None
        """
        cursor = self.db.cursor()
        for label_id in labels:
            cursor.execute("""
                           INSERT INTO LabelInVelp(label_id, velp_id)
                           VALUES (?, ?)
                           """, [label_id, velp_id]
                           )
        self.db.commit()

    def get_velp_label_ids(self, assessment_area: AssessmentArea) -> List[Dict]:
        """Get labels for velps that are linked to an assessment area.

        :param assessment_area: the relevant assessment area
        :return: A list of dictionaries, each representing a single label-velp link.
        """
        cursor = self.db.cursor()
        cursor.execute("""
                       SELECT
                         LabelInVelp.velp_id,
                         LabelInVelp.label_id AS labels
                       FROM LabelInVelp
                       WHERE velp_id IN (
                       """ +
                       assessment_area.get_sql_for_velp_ids()
                       + """
                       )
                       ORDER BY velp_id ASC
                       """, assessment_area.get_parameters_for_velp_ids()
                       )
        results = self.resultAsDictionary(cursor)
        return results

    def get_document_velp_label_ids(self, document_id: int) -> List[Dict]:
        """Get labels for velps that are linked to a document.

        :param document_id: Id of the document
        :return: A list of dictionaries, each representing a single label-velp link.
        """
        return self.get_velp_label_ids(assessment_area_from_document(document_id))

    def get_velp_label_content(self, assessment_area: AssessmentArea, language_id: str = 'FI') -> List[Dict]:
        """Get label content for labels that are linked to an assessment area.

        :param assessment_area: the relevant assessment area
        :param language_id: Optional, Id of the requested language of the content. Default is 'FI'
        :return: A list of dictionaries with each dictionary representing a single label.
        """
        cursor = self.db.cursor()
        cursor.execute("""
                       SELECT Label.id, Label.content
                       FROM Label
                       WHERE label.language_id = ? AND label.id IN (
                         SELECT DISTINCT LabelInVelp.label_id
                         FROM LabelInVelp
                         WHERE LabelInVelp.velp_id IN (
                       """ +
                       assessment_area.get_sql_for_velp_ids()
                       + """
                         )
                       )
                       """, [language_id] + assessment_area.get_parameters_for_velp_ids()
                       )
        results = self.resultAsDictionary(cursor)
        return results

    def get_document_velp_label_content(self, document_id: int, language_id: str = 'FI') -> List[Dict]:
        """Get label content for labels that are linked to a document.

        :param document_id: ID for the document.
        :param language_id: Optional, Id of the requested language. Default is 'FI'.
        :return: List of labels, each label represented by a dictionary
        """
        return self.get_velp_label_content(assessment_area_from_document(document_id), language_id)

    def delete_label(self, label_id: int):
        """
        Deletes label (use with extreme caution)
        :param label_id: Label ID
        :return:
        """
        cursor = self.db.cursor()
        cursor.execute("""
                      DELETE
                      FROM Label
                      WHERE id = ?
                      """, [label_id]
                       )
        self.db.commit()
