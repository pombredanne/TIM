from timroutetest import TimRouteTest


class ManageTest(TimRouteTest):
    def test_manage(self):
        self.login_test1()
        doc = self.create_doc(initial_par='testing manage').document
        self.get('/manage/' + str(doc.doc_id), expect_status=200)
        self.get('/notify/' + str(doc.doc_id), expect_status=200, as_json=True,
                 expect_content={"email_doc_modify": False,
                                 "email_comment_add": False,
                                 "email_comment_modify": False
                                 })

        for new_settings in {"email_doc_modify": True,
                             "email_comment_add": False,
                             "email_comment_modify": False
                             }, {"email_doc_modify": False,
                                 "email_comment_add": True,
                                 "email_comment_modify": True
                                 }:
            self.json_post('/notify/' + str(doc.doc_id), new_settings, expect_status=200)
            self.get('/notify/' + str(doc.doc_id), expect_status=200, as_json=True, expect_content=new_settings)
