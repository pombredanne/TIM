
"""
    Updates the notes and readings to the new database format.
"""

from timdb.gitclient import customCommit, gitCommand, getFileVersion
from timdb.timdb2 import TimDb
from timdb.timdbbase import TimDbBase, DocIdentifier
import sqlite3
import os
import sys

def createparmappings(cursor):
    cursor.execute(
        """
        CREATE TABLE ParMappings(
        doc_id INTEGER NOT NULL,
        doc_ver INTEGER NOT NULL,
        par_index INTEGER NOT NULL,
        new_ver INTEGER NULL,
        new_index INTEGER NULL,
        modified BOOLEAN NULL,

        CONSTRAINT ParMappings_PK
            PRIMARY KEY (doc_id, doc_ver, par_index)
        )
        ;
        """, []
    )

def createusernotes(cursor):
    cursor.execute(
        """
        CREATE TABLE UserNotes(
        UserGroup_id	INTEGER NOT NULL,
        doc_id INTEGER NOT NULL,
        doc_ver INTEGER NOT NULL,
        par_index INTEGER NOT NULL,
        note_index INTEGER NOT NULL,
        content VARCHAR(255) NOT NULL,
        created TIMESTAMP NOT NULL,
        modified TIMESTAMP NULL,
        access VARCHAR(20) NOT NULL,
        tags VARCHAR(20) NOT NULL,

        CONSTRAINT UserNotes_PK
            PRIMARY KEY (UserGroup_id, doc_id, doc_ver, par_index, note_index),

        CONSTRAINT UserNotes_id
            FOREIGN KEY (doc_id, doc_ver, par_index)
            REFERENCES ParMappings (doc_id, doc_ver, par_index)
                ON DELETE CASCADE
                ON UPDATE RESTRICT
        );
        """, []
    )

def createreadparagraphs(cursor):
    cursor.execute(
        """
        CREATE TABLE ReadParagraphs(
        UserGroup_id	INTEGER NOT NULL,
        doc_id INTEGER NOT NULL,
        doc_ver INTEGER NOT NULL,
        par_index INTEGER NOT NULL,
        timestamp TIMESTAMP NOT NULL,

        CONSTRAINT ReadParagraphs_PK
            PRIMARY KEY (UserGroup_id, doc_id, doc_ver, par_index),

        CONSTRAINT ReadParagraphs_id
            FOREIGN KEY (doc_id, doc_ver, par_index)
            REFERENCES ParMappings (doc_id, doc_ver, par_index)
                ON DELETE CASCADE
                ON UPDATE RESTRICT
        );
        """, []
    )

def dropnewtables(cursor):
    cursor.execute("DROP TABLE ParMappings")
    cursor.execute("DROP TABLE ReadParagraphs")
    cursor.execute("DROP TABLE UserNotes")

def write_progress(status):
    sys.stdout.write("\r%d%%" % (status * 100))
    sys.stdout.flush()

def print_stats(ok, inv):
    sys.stdout.write("\r\n")
    sys.stdout.flush()
    print("{0} entries successfully converted".format(ok))
    if inv > 0:
        print("{0} invalid / duplicate entries".format(inv))
    print("")

def upgrade_readings(timdb):
    cursor = timdb.db.cursor()
    cursor.execute("select id, UserGroup_id, description, created, modified from Block where type_id = 5")
    i = 0
    inv = 0
    ok = 0
    data = cursor.fetchall()
    log = open('upgrade_readings.log', 'w')
    for b_id, b_grp, b_desc, b_created, b_modified in data:
        i += 1
        write_progress(i / len(data))
        
        if not timdb.users.groupExists(b_grp):
            log.write("User group {0} does not exist, skipping.\n".format(b_grp))
            inv += 1
            continue
            
        cursor.execute(
            """
            select parent_block_specifier, parent_block_id
            from BlockRelation where block_id = ?
            """, [b_id])
        rel = cursor.fetchone()
        if rel is None:
            log.write('Encountered a reading with no relation (block id %d), ignored.\n' % b_id)
            inv += 1
            continue

        r_parspec, r_parid = rel
        
        if not timdb.documents.documentExists(DocIdentifier(r_parid, '')):
            log.write("Document {0} does not exist, skipping.\n".format(r_parid))
            inv += 1
            continue

        versions = timdb.documents.getDocumentVersions(r_parid)
        version = versions[0]['hash']
        if len(versions) > 1:
            blocks = timdb.documents.getDocumentAsBlocks(DocIdentifier(r_parid, version))
            if blocks[r_parspec] != b_desc:
                # Set reading to the oldest version... marks it as modified
                latest = version
                version = versions[len(versions) - 1]['hash']
                # Add a paragraph mapping
                cursor.execute(
                    """
                    insert into ParMappings (doc_id, doc_ver, par_index, new_ver, new_index, modified)
                    values (?, ?, ?, ?, ?, 'True')
                    """, [r_parid, version, r_parspec, latest, r_parspec]
                )

        try:
            cursor.execute(
                """
                insert into ReadParagraphs (UserGroup_id, doc_id, doc_ver, par_index, timestamp)
                values (?, ?, ?, ?, ?)
                """, [b_grp, r_parid, version, r_parspec, b_created]
            )
        except sqlite3.IntegrityError:
            log.write('Reading for user group {0} doc {1} paragraph {2} already marked.\n'.format(b_grp, r_parid, r_parspec))
            inv += 1
            continue
        
        ok += 1

    log.close()
    print_stats(ok, inv)
    timdb.db.commit()

def try_insert_block_relation(cursor, block_id, doc_id, par_index):
    while True:
        try:
            cursor.execute(
                """
                insert into BlockRelation
                (parent_block_specifier, parent_block_revision_id, parent_block_id, block_id)
                values (?, 0, ?, ?)
                """, [par_index, doc_id, block_id]
            )
            return True
        except sqlite3.IntegrityError:
            print('Relation for block {0} already exists.'.format(block_id))
            c = input('Overwrite (y = yes, n = no, a = abort, Enter to retry)? ')
            if c == 'y':
               cursor.execute('delete from BlockRelation where block_id = ?',  [block_id])
               cursor.execute('delete from BlockViewAccess where block_id = ?',  [block_id])
               cursor.execute('delete from BlockEditAccess where block_id = ?',  [block_id])
            elif c == 'n':
                tried = True
            elif c == 'a':
                print("Aborting.")
                return False

def downgrade_readings(timdb):
    cursor = timdb.db.cursor()
    i = 0
    ok = 0

    cursor.execute("select UserGroup_id, doc_id, par_index, timestamp from ReadParagraphs")
    data = cursor.fetchall()
    for grp_id, doc_id, par_index, timestamp in data:
        i += 1
        write_progress(i / len(data))

        cursor.execute(
            """
            insert into Block (latest_revision_id, type_id, description, created, UserGroup_id)
            values (0, 5, ?, ?, ?)
            """, ['', timestamp, grp_id]
        )
        block_id = cursor.lastrowid
        if not try_insert_block_relation(cursor, block_id, doc_id, par_index):
            return
        ok += 1
        
    print_stats(ok, 0)
    timdb.db.commit()

def strtotags(tagstr):
    tags = []
    if 'd' in tagstr:
        tags.append("difficult")
    if 'u' in tagstr:
        tags.append("unclear")
    return tags

def tagstostr(tags):
    tagstr = ''
    if 'difficult' in tags:
        tagstr += 'd'
    if 'unclear' in tags:
        tagstr += 'u'
    return tagstr

def downgrade_notes(timdb):
    cursor = timdb.db.cursor()
    cursor.execute("select UserGroup_id, doc_id, par_index, content, created, modified, access, tags from UserNotes")
    assert_notesdir()
    blockpath = os.path.join(FILES_ROOT_PATH, 'blocks', 'notes')
    i = 0
    ok = 0
    data = cursor.fetchall()
    for grp_id, doc_id, par_index, content, created, modified, access, tags in data:
        i += 1
        write_progress(i / len(data))
        
        cursor.execute(
            """
            insert into Block (latest_revision_id, type_id, description, created, modified, UserGroup_id)
            values (0, 2, ?, ?, ?, ?)
            """, [",".join(strtotags(tags)), created, modified, grp_id]
        )
        block_id = cursor.lastrowid

        if not try_insert_block_relation(cursor, block_id, doc_id, par_index):
            return

        blockfile = timdb.notes.getBlockPath(int(block_id))
        timdb.notes.writeUtf8(content, blockfile)
        gitCommand(blockpath, 'add ' + str(block_id))
        if access == 'everyone':
            timdb.users.grantViewAccess(0, block_id)
        ok += 1
    
    print_stats(ok, 0)
    timdb.db.commit()
    commit_files('Added notes and paragraphs.')

def upgrade_notes(timdb):
    cursor = timdb.db.cursor()
    cursor.execute("select id, UserGroup_id, description, created, modified from Block where type_id = 2")
    i = 0
    ok = 0
    inv = 0
    data = cursor.fetchall()
    log = open('update_notes.log', 'w')
    for b_id, b_grp, b_desc, b_created, b_modified in data:
        i += 1
        write_progress(i / len(data))
        
        if not timdb.users.groupExists(b_grp):
            log.write("User group {0} does not exist, skipping.\n".format(b_grp))
            inv += 1
            continue
            
        cursor.execute(
            """
            select parent_block_specifier, parent_block_id
            from BlockRelation where block_id = ?
            """, [b_id])
        rel = cursor.fetchone()
        if rel is None:
            log.write('Encountered a note with no relation (block id %d), ignored.\n' % b_id)
            inv += 1
            continue

        r_parspec, r_parid = rel
        
        if not timdb.documents.documentExists(DocIdentifier(r_parid, '')):
            log.write("Document {0} does not exist, skipping.\n".format(r_parid))
            inv += 1
            continue
        
        version = timdb.documents.getNewestVersion(r_parid)['hash']
        tagstr = tagstostr(b_desc.split(',')) if b_desc is not None else ''

        with open(timdb.notes.getBlockPath(b_id), 'r', encoding='utf-8') as f:
            content = f.read()

        if timdb.users.userGroupHasViewAccess(0, b_id):
            access = 'everyone'
        else:
            access = 'justme'

        cursor.execute(
           """
           select note_index from UserNotes where UserGroup_id = ? and doc_id = ? and par_index = ?
           order by note_index desc
           """, [b_grp, r_parid, r_parspec]
        )
        indexrows = cursor.fetchone()
        note_index = indexrows[0] + 1 if indexrows is not None else 0
        group_id = timdb.users.getUserGroups(b_grp)[0]['id']

        if b_created is None or b_created == '':
            cursor.execute(
                """
                insert into UserNotes
                (UserGroup_id, doc_id, doc_ver, par_index, note_index, content, created, access, tags)
                values (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
                """, [b_grp, r_parid, version, r_parspec, note_index, content, access, tagstr]
            )
        else:
            cursor.execute(
                """
                insert into UserNotes
                (UserGroup_id, doc_id, doc_ver, par_index, note_index, content, created, modified, access, tags)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [b_grp, r_parid, version, r_parspec, note_index, content, b_created, b_modified, access, tagstr]
            )


        ok += 1

    log.close()
    print_stats(ok, inv)
    timdb.db.commit()

def delete_old(timdb):
    cursor = timdb.db.cursor()
    
    cursor.execute("select id from Block where type_id = 5")
    for row in cursor.fetchall():
        cursor.execute("delete from BlockRelation where Block_id = ?", [row[0]])
        cursor.execute("delete from BlockViewAccess where Block_id = ?", [row[0]])
        cursor.execute("delete from BlockEditAccess where Block_id = ?", [row[0]])
    cursor.execute("delete from Block where type_id = 5")
    
    cursor.execute("select id from Block where type_id = 2")
    assert_notesdir()
    gitCommand(FILES_ROOT_PATH, 'add blocks/notes')
    for row in cursor.fetchall():
        cursor.execute("delete from BlockRelation where Block_id = ?", [row[0]])
        cursor.execute("delete from BlockViewAccess where Block_id = ?", [row[0]])
        cursor.execute("delete from BlockEditAccess where Block_id = ?", [row[0]])
        
        blockpath = os.path.join(FILES_ROOT_PATH, 'blocks', 'notes')
        gitCommand(blockpath, 'rm ' + str(row[0]))
        #os.remove(timdb.notes.getBlockPath(b_id))        
    cursor.execute("delete from Block where type_id = 2")
    
    timdb.db.commit()
    commit_files('Deleted old notes and paragraphs.')

def assert_notesdir():
    blockpath = os.path.join(FILES_ROOT_PATH, 'blocks', 'notes')
    if not os.path.exists(blockpath):
        os.mkdir(blockpath)
        
    cwd = os.getcwd()
    os.chdir(FILES_ROOT_PATH)
    
    if getFileVersion('blocks', 'notes') == 0:
        gitCommand('.', 'add blocks/notes')
        #customCommit('', 'Added notes directory.', 'update_notes.py', include_staged_files=True)

    os.chdir(cwd)

def commit_files(msg):
    cwd = os.getcwd()
    os.chdir(FILES_ROOT_PATH)
    customCommit('', msg, 'update_notes.py', include_staged_files=True)
    os.chdir(cwd)

def getcount(cursor, table_name, condition = None):
    try:
        if condition is None:
            cursor.execute("select * from %s" % table_name)
        else:
            cursor.execute("select * from %s where %s" % (table_name, condition))
        return len(cursor.fetchall())
    except sqlite3.OperationalError:
        return -1

def inform(description, count):
    if count < 0:
        print("The %s table does not exist." % description)
    else:
        print("Found %d %s" % (count, description))

def cprint(text, condition):
    if condition:
        print(text)

if __name__ == "__main__":
    global FILES_ROOT_PATH

    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    FILES_ROOT_PATH = 'tim_files'
    timdb = TimDb(db_path='tim_files/tim.db', files_root_path=FILES_ROOT_PATH)

    cursor = timdb.db.cursor()
    c = ''

    while c != 'q':
        pmcount = getcount(cursor, 'ParMappings')
        rpcount = getcount(cursor, 'ReadParagraphs')
        notecount = getcount(cursor, 'UserNotes')
        oldrpcount = getcount(cursor, 'Block', 'type_id = 5')
        oldnotecount = getcount(cursor, 'Block', 'type_id = 2')

        inform("users", getcount(cursor, 'User') - 1)
        inform("user groups", getcount(cursor, 'UserGroup') - 1)
        inform("old format read paragraphs", oldrpcount)
        inform("old format notes", oldnotecount)
        inform("paragraph mappings", pmcount)
        inform("new format read paragraphs", rpcount)
        inform("new format notes", notecount)

        cprint("'u' to upgrade everything to the new format", oldnotecount > 0 or oldrpcount > 0)
        cprint("'d' to downgrade everything", notecount > 0 or rpcount > 0)
        cprint("'c' to create the new tables", pmcount < 0 or rpcount < 0 or notecount < 0)
        cprint("'dn' to delete the new tables", pmcount >= 0 or rpcount >= 0 or notecount >= 0)
        cprint("'do' to delete the old format notes & read markings", oldrpcount > 0 or oldnotecount > 0)
        print("'q' to quit.")

        c = input(">")

        if (c == 'c' or c == 'u') and (pmcount < 0 or rpcount < 0 or notecount < 0):
            print("Creating the new tables.")
            if pmcount < 0:
                print('...ParMappings')
                createparmappings(cursor)
            if rpcount < 0:
                print('...ReadParagraphs')
                createreadparagraphs(cursor)
            if notecount < 0:
                print('...UserNotes')
                createusernotes(cursor)

        if c == 'u' and (oldnotecount > 0 or oldrpcount > 0):
            print("Upgrading readings...")
            upgrade_readings(timdb)
            print("Upgrading notes...")
            upgrade_notes(timdb)

        elif c == 'd' and (notecount > 0 or rpcount > 0):
            print("Downgrading readings...")
            downgrade_readings(timdb)
            print("Downgrading notes...")
            downgrade_notes(timdb)

        elif c == 'dn' and (pmcount >= 0 or rpcount >= 0 or notecount >= 0):
            print("Deleting the new tables.")
            dropnewtables(cursor)

        elif c == 'do' and (oldrpcount > 0 or oldnotecount > 0):
            print("Deleting the old format data.")
            delete_old(timdb)
            
        elif c == 'q':
            print("Exiting.")

        else:
            print("Unrecognized command.")

        print("")

