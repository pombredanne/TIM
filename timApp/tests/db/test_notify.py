from tests.db.timdbtest import TimDbTest
from timdb.tim_models import db


class NotifyTest(TimDbTest):
    def test_notify(self):
        d = self.create_doc()
        n = self.test_user_1.get_notify_settings(d)
        self.assertFalse(n.email_comment_add)
        self.assertFalse(n.email_comment_modify)
        self.assertFalse(n.email_doc_modify)
        self.test_user_1.set_notify_settings(d, doc_modify=True, comment_add=True, comment_modify=True)
        db.session.commit()
        n = self.test_user_1.get_notify_settings(d)
        self.assertTrue(n.email_comment_add)
        self.assertTrue(n.email_comment_modify)
        self.assertTrue(n.email_doc_modify)
        self.test_user_1.set_notify_settings(d, doc_modify=False, comment_add=True, comment_modify=True)
        db.session.commit()
        n = self.test_user_1.get_notify_settings(d)
        self.assertTrue(n.email_comment_add)
        self.assertTrue(n.email_comment_modify)
        self.assertFalse(n.email_doc_modify)
