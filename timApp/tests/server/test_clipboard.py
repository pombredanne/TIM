import random
from typing import Optional

from timApp.documentmodel.docparagraph import DocParagraph
from timApp.tests.server.timroutetest import TimRouteTest
from timApp.timdb.models.docentry import DocEntry
from timApp.timdb.readparagraphtype import ReadParagraphType


class ClipboardTest(TimRouteTest):
    def copy(self,
             doc: DocEntry,
             par_start: DocParagraph,
             par_end: DocParagraph, **kwargs):
        self.json_post('/clipboard/copy/{}/{}/{}'.format(doc.id, par_start.get_id(), par_end.get_id()), **kwargs)

    def cut(self,
            doc: DocEntry,
            par_start: DocParagraph,
            par_end: DocParagraph, **kwargs):
        self.json_post('/clipboard/cut/{}/{}/{}'.format(doc.id, par_start.get_id(), par_end.get_id()), **kwargs)

    def paste(self,
              doc: DocEntry,
              par_before: Optional[DocParagraph] = None,
              par_after: Optional[DocParagraph] = None,
              as_ref: bool = False, **kwargs):
        self.json_post('/clipboard/paste/{}'.format(doc.id),
                       {'par_before': par_before.get_id() if par_before else None,
                        'par_after': par_after.get_id() if par_after else None,
                        'as_ref': as_ref}, **kwargs)

    def test_invalid(self):
        self.login_test2()
        d = self.create_doc(initial_par=['test1', 'test2', 'test3'])
        pars = d.document.get_paragraphs()
        self.cut(d,
                 DocParagraph.create(par_id='a', doc=d.document),
                 DocParagraph.create(par_id='b', doc=d.document),
                 expect_status=400,
                 expect_content={'error': 'Paragraph not found: a'})
        self.copy(d,
                  DocParagraph.create(par_id='a', doc=d.document),
                  DocParagraph.create(par_id='b', doc=d.document),
                  expect_status=400,
                  expect_content={'error': 'Paragraph not found: a'})
        self.paste(d,
                   DocParagraph.create(par_id='a', doc=d.document),
                   expect_status=400,
                   expect_content={'error': 'The clipboard is empty.'})
        self.cut(d,
                 pars[0],
                 DocParagraph.create(par_id='b', doc=d.document),
                 expect_status=400,
                 expect_content={'error': 'Paragraph not found: b'})
        self.cut(d,
                 DocParagraph.create(par_id='b', doc=d.document),
                 pars[0],
                 expect_status=400,
                 expect_content={'error': 'Paragraph not found: b'})
        self.copy(d,
                  pars[0],
                  DocParagraph.create(par_id='b', doc=d.document),
                  expect_status=400,
                  expect_content={'error': 'Paragraph not found: b'})
        self.copy(d,
                  DocParagraph.create(par_id='b', doc=d.document),
                  pars[0],
                  expect_status=400,
                  expect_content={'error': 'Paragraph not found: b'})

        self.cut(d,
                 pars[0],
                 pars[0])
        self.paste(d,
                   pars[0],
                   expect_status=400,
                   expect_content={'error': 'Paragraph not found: {}'.format(pars[0].get_id())})

    def test_copy_one(self):
        self.login_test1()
        test_pars = ['test1', 'test2', 'test3']
        d = self.create_doc(initial_par=test_pars)
        pars = d.document.get_paragraphs()
        self.copy(d, pars[0], pars[0])
        self.paste(d, par_after=pars[2])
        d.document.clear_mem_cache()
        pars_new = d.document.get_paragraphs()
        self.assertListEqual(test_pars, [p.get_markdown() for p in pars_new[0:3]])
        self.assertTrue(pars_new[0].is_same_as(pars_new[3]))

    def test_copy_many(self):
        self.login_test1()
        test_pars = ['test1', 'test2', 'test3', 'test4']
        d = self.create_doc(initial_par=test_pars)
        pars = d.document.get_paragraphs()
        timdb = self.get_db()
        timdb.readings.mark_read(usergroup_id=self.current_group().id,
                                 doc=d.document,
                                 par=pars[0],
                                 read_type=ReadParagraphType.click_red)
        timdb.readings.mark_read(usergroup_id=self.current_group().id,
                                 doc=d.document,
                                 par=pars[0],
                                 read_type=ReadParagraphType.hover_par)
        timdb.readings.mark_read(usergroup_id=self.current_group().id,
                                 doc=d.document,
                                 par=pars[1],
                                 read_type=ReadParagraphType.hover_par)
        self.copy(d, pars[0], pars[2])
        self.paste(d, par_after=pars[2])
        d.document.clear_mem_cache()
        pars_new = d.document.get_paragraphs()
        new_readings = timdb.readings.get_readings(self.current_group().id, d.document)
        self.assertEqual(6, len(new_readings))
        self.assertEqual(2, len(list(filter(lambda r: r.type == ReadParagraphType.click_red, new_readings))))
        self.assertEqual(4, len(list(filter(lambda r: r.type == ReadParagraphType.hover_par, new_readings))))
        self.assertListEqual(['test1', 'test2', 'test3', 'test1', 'test2', 'test3', 'test4'],
                             [p.get_markdown() for p in pars_new])

    def test_copy_to_empty(self):
        self.login_test1()
        d = self.create_doc(initial_par=['test1', 'test2'])
        pars = d.document.get_paragraphs()

        d2 = self.create_doc()
        self.copy(d, pars[0], pars[1])
        self.paste(d2, par_after=DocParagraph.help_par())
        d2_pars = d2.document.get_paragraphs()
        self.assertEqual(pars, d2_pars)

        d3 = self.create_doc()
        self.copy(d, pars[0], pars[1])
        self.paste(d3, par_before=DocParagraph.help_par())
        d3_pars = d3.document.get_paragraphs()
        self.assertEqual(pars, d3_pars)

    def test_random_actions(self):
        self.login_test1()
        d = self.create_doc(initial_par="""
#- {area=a1}
#- {area_end=a1}
#- {area=a2}
#-
test
#- {area_end=a2}
#- {area=a3}
#-
test
#- {area=a4}
#-
test
#-
test
#- {area_end=a4}
#-
test
#-
test
#-
test
#- {area_end=a3}
#-
test
#-
test
#- {area=a5}
#-
test
#-
test
#- {area_end=a5}
""".replace('area', 'xxx'))
        random.seed(0)
        message = ""
        for i in range(0, 10):
            d.document.clear_mem_cache()
            pars = d.document.get_paragraphs()
            ids = [p.get_id() for p in pars]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(21, len(pars), msg=message)
            first: DocParagraph = random.choice(pars)
            second: DocParagraph = random.choice(pars)
            first_index = pars.index(first)
            second_index = pars.index(second)
            if first_index > second_index:
                first_index, second_index = second_index, first_index
            del pars[first_index:second_index + 1]
            if not pars:
                continue
            pos = random.choice(pars)
            is_before = random.choice((True, False))
            message = """
First: {}, second: {}, pos: {}, is_before: {}
Index 1: {}, index 2: {}

Document:

{}
            """.format(first.get_id(), second.get_id(), pos.get_id(), is_before,
                       first_index, second_index, d.document.export_markdown())

            self.cut(d, first, second)
            d.document.clear_mem_cache()
            pars = d.document.get_paragraphs()

            self.assertEqual(21 - abs(first_index - second_index) - 1, len(pars), msg=message)
            new_ids = [p.get_id() for p in pars]
            self.assertNotIn(first.get_id(), new_ids)
            self.assertNotIn(second.get_id(), new_ids)

            if is_before:
                self.paste(d, par_before=pos)
            else:
                self.paste(d, par_after=pos)
