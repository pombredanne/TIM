"""Server tests for preamble."""
from lxml import html
from unittest.mock import patch, Mock

from timApp.documentmodel.specialnames import TEMPLATE_FOLDER_NAME, PREAMBLE_FOLDER_NAME, DEFAULT_PREAMBLE_DOC
from timApp.tests.server.timroutetest import TimRouteTest
from timApp.timdb.docinfo import DocInfo


class PreambleTestBase(TimRouteTest):
    def create_doc_and_preamble(self, folder: str):
        d = self.create_doc(f'{folder}/a/b/test1')
        p2 = self.create_doc(f'{folder}/a/{TEMPLATE_FOLDER_NAME}/{PREAMBLE_FOLDER_NAME}/{DEFAULT_PREAMBLE_DOC}')
        p1 = self.create_doc(f'{folder}/{TEMPLATE_FOLDER_NAME}/{PREAMBLE_FOLDER_NAME}/{DEFAULT_PREAMBLE_DOC}')
        p3 = self.create_doc(f'{folder}/a/b/{TEMPLATE_FOLDER_NAME}/{PREAMBLE_FOLDER_NAME}/{DEFAULT_PREAMBLE_DOC}')
        p1.document.set_settings({'macros': {'a': 'cat', 'b': 'dog', 'd': 'sheep'}})
        p2.document.set_settings({'macros': {'b': 'mouse', 'c': 'giraffe'}})
        p3.document.set_settings({'macros': {'c': 'elephant', 'd': 'fly'}})
        return d, p1, p2, p3


class PreambleTest(PreambleTestBase):
    def test_preamble_settings(self):
        self.login_test1()
        folder = self.current_user.get_personal_folder().path
        d, p1, p2, p3 = self.create_doc_and_preamble(folder)
        d.document.set_settings({'macros': {'e': 'fox'}})

        d_no_preamble = self.create_doc(f'{folder}/a/b/nopreamble')
        self.assertEqual([p.path_without_lang for p in d.get_preamble_docs()],
                         [
                             f'users/test-user-1/{TEMPLATE_FOLDER_NAME}/{PREAMBLE_FOLDER_NAME}/{DEFAULT_PREAMBLE_DOC}',
                             f'users/test-user-1/a/{TEMPLATE_FOLDER_NAME}/{PREAMBLE_FOLDER_NAME}/{DEFAULT_PREAMBLE_DOC}',
                             f'users/test-user-1/a/b/{TEMPLATE_FOLDER_NAME}/{PREAMBLE_FOLDER_NAME}/{DEFAULT_PREAMBLE_DOC}'
                         ])
        self.assertEqual(d.document.get_settings().get_dict()['macros'],
                         {'a': 'cat', 'b': 'mouse', 'c': 'elephant', 'd': 'fly', 'e': 'fox'})

        d_no_preamble.document.set_settings({'preamble': None})
        self.assertEqual(d_no_preamble.document.get_settings().get_dict(), {'preamble': None})

        self.assertEqual(p1.document.get_settings().get_dict()['macros'], {'a': 'cat', 'b': 'dog', 'd': 'sheep'})
        self.assertEqual(p2.document.get_settings().get_dict()['macros'],
                         {'b': 'mouse', 'c': 'giraffe'})
        self.assertEqual(p3.document.get_settings().get_dict()['macros'],
                         {'c': 'elephant', 'd': 'fly'})

    def test_preamble_content(self):
        self.login_test2()
        folder = self.current_user.get_personal_folder().path
        d, p1, p2, p3 = self.create_doc_and_preamble(folder)
        d.document.set_settings({'macros': {'e': 'fox'}})
        p1.document.add_text('p1')
        p2.document.add_text('p2')
        p3.document.add_text('p3 %%e%% s')
        d.document.add_text('own')
        elem = self.get(d.url, as_tree=True)
        self.assert_content(elem, ['p1', 'p2', 'p3 fox s', '', 'own'])

    def test_preamble_self(self):
        self.login_test3()
        folder = self.current_user.get_personal_folder().path
        d, p1, p2, p3 = self.create_doc_and_preamble(folder)
        p1.document.add_text('p1')
        p2.document.add_text('p2')
        p3.document.add_text('p3')
        self.get(p1.url)

    def test_preamble_perf(self):
        self.login_test1()
        d = self.create_doc()
        with patch.object(DocInfo, '_get_preamble_docs_impl') as m:  # type: Mock
            self.get(d.url)
        m.assert_called_once()


class PreambleTest2(PreambleTestBase):
    def test_preamble_unique_ids(self):
        self.login_test1()
        folder = self.current_user.get_personal_folder().path
        d, p1, p2, p3 = self.create_doc_and_preamble(folder)
        par = p1.document.add_text('test')[0]
        d.document.add_paragraph('test', par_id=par.get_id())
        self.get(d.url, expect_contains='The paragraphs in the main document must '
                                        'have distinct ids from the preamble documents. Conflicting ids:')

        p2.document.add_paragraph('test', par_id=par.get_id())
        self.get(d.url, expect_contains='The paragraphs in preamble documents must have distinct ids among themselves.')

    def test_preamble_area_settings(self):
        self.login_test2()
        folder = self.current_user.get_personal_folder().path
        d, p1, p2, p3 = self.create_doc_and_preamble(folder)
        p1.document.add_text("""
#- {area=a settings=""}
a: b

#- {area_end=a}
""")
        resp = self.get(d.url, as_tree=True)

        # There should not be warnings about missing areas.
        alert = resp.cssselect('.alert.alert-info')
        self.assertFalse(alert)

    def test_preamble_heading_numbering(self):
        self.login_test3()
        folder = self.current_user.get_personal_folder().path
        d, p1, p2, p3 = self.create_doc_and_preamble(folder)
        p1.document.add_text('# a')
        p2.document.add_text('# b')
        p3.document.add_text('# c')
        p1.document.set_settings({'auto_number_headings': 1})
        d.document.add_text('# d')
        doc = self.get(d.url, as_tree=True)
        self.assert_content(doc, ['1. a', '2. b', '3. c', '4. d'])
        pars = d.document.get_paragraphs()
        first_par = pars[0]
        e = self.json_post(f'/preview/{d.id}', {'text': '# d', 'par': first_par.get_id()},
                           json_key='texts', as_tree=True)
        self.assert_content(e, ['4. d'])
        e = self.json_post(f'/preview/{d.id}', {'text': '# d', 'par_next': first_par.get_id()},
                           json_key='texts', as_tree=True)
        self.assert_content(e, ['4. d'])

        self.post_par(d.document, '# x', first_par.get_id())
        e = self.get_updated_pars(d)
        changed = e['changed_pars']
        self.assert_content(html.fromstring(changed[first_par.get_id()]), ['4. x'])
