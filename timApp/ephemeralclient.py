'''
An Ephemeral client that can communicate with Ephemeral server.
'''
import requests
from contracts import contract, new_contract

new_contract('bytes', bytes)
new_contract('Response', requests.Response)

class EphemeralException(Exception):
    pass

class NotInCacheException(Exception):
    pass

class EphemeralClient(object):
    
    @contract
    def __init__(self, server_path : 'str'):
        """Initializes EphemeralClient with the specified server path."""
        self.server_path = server_path

    @contract
    def addBlock(self, document_id : 'int', next_block_id : 'int', content : 'str') -> 'bool':
        """Adds a block to a document.
        
        :param document_id: The id of the document.
        :param next_block_id: The id of the following block.
        :param content: The content of the block.
        """
        
        # NOTE: Ephemeral doesn't support adding blocks yet.
        try:
            r = requests.post(url=self.server_path + '/new/{}/{}'.format(document_id, next_block_id), data=bytes(content, encoding='utf-8'))
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        r.encoding = 'utf-8'
        self.__raiseExceptionIfBlockNotFound(r)
        
        return True

    @contract
    def deleteBlock(self, document_id : 'int', block_id : 'int') -> 'bool':
        """Deletes a block from a document.
        
        :param document_id: The id of the document.
        :param block_id: The id of the block to be deleted.
        :returns: True if deletion was successful, false otherwise.
        """
        
        try:
            r = requests.put(url=self.server_path + '/delete/{}/{}'.format(document_id, block_id), data="Filler")
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        r.encoding = 'utf-8'
        self.__raiseExceptionIfBlockNotFound(r)
        
        return True

    @contract
    def diff(self, first_document_id : 'int', second_document_id : 'int') -> 'str':
        """Performs a diff between two documents.
        
        :param first_document_id: The id of the first document.
        :param second_document_id: The id of the second document.
        :returns: (TODO)
        """
        
        try:
            r = requests.get(url=self.server_path + '/diff/{}/{}'.format(first_document_id, second_document_id))
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        r.encoding = 'utf-8'
        self.__raiseExceptionIfDocumentNotFound(r)
        return r.text
    
    @contract
    def diff3(self, first_document_id : 'int', second_document_id : 'int', third_document_id : 'int') -> 'str':
        """Performs a diff among three documents.
        
        :param first_document_id: The id of the first document.
        :param second_document_id: The id of the second document.
        :param third_document_id: The id of the third document.
        :returns: The diff3 output (TODO: what format?).
        """
        
        try:
            r = requests.get(url=self.server_path + '/diff3/{}/{}/{}'.format(first_document_id, second_document_id, third_document_id))
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        r.encoding = 'utf-8'
        self.__raiseExceptionIfDocumentNotFound(r)
        return r.text
    
    @contract
    def getBlock(self, document_id : 'int', block_id : 'int') -> 'str':
        """Gets an individual block from a document.
        
        :param document_id: The id of the document.
        :param block_id: The id of the block.
        :returns: The content of the block.
        """
        
        try:
            r = requests.get(url=self.server_path + '/{}/{}'.format(document_id, block_id))
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        r.encoding = 'utf-8'
        self.__raiseExceptionIfBlockNotFound(r)
        return r.text
    
    @contract
    def getBlockMapping(self, first_document_id : 'int', second_document_id : 'int'):
        """Gets a mapping of blocks between two documents.
        
        :param first_document_id: The id of the first document.
        :param second_document_id: The id of the second document.
        :returns: The mapping of blocks between the two documents.
        """
        
        try:
            r = requests.get(url=self.server_path + '/mapDocuments/{}/{}'.format(first_document_id, second_document_id))
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        return r.json()
        
    @contract
    def __raiseExceptionIfBlockNotFound(self, r : 'Response'):
        """Raises EphemeralException if the response contains 'no block found'.
        
        :param response: The response string.
        """
        
        if r.status_code == 404:
            raise NotInCacheException('The requested block was not found.')

    @contract
    def __raiseExceptionIfDocumentNotFound(self, r : 'Response'):
        """Raises EphemeralException if the response contains 'no block found'.
        
        :param response: The response string.
        """
        if r.status_code == 404:
            raise NotInCacheException('The requested document was not found.')

    @contract
    def getBlockAsHtml(self, document_id : 'int', block_id : 'int') -> 'str':
        """Gets an individual block from a document.
        
        :param document_id: The id of the document.
        :param block_id: The id of the block.
        :returns: The content of the block.
        """
        
        try:
            r = requests.get(url=self.server_path + '/{}/{}/html'.format(document_id, block_id))
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        r.encoding = 'utf-8'
        self.__raiseExceptionIfBlockNotFound(r)
        return r.text
    
    @contract
    def getDocumentAsHtmlBlocks(self, document_id: 'int') -> 'list(str)':
        """Gets the document as a list of HTML blocks.
        
        :param document_id: The id of the document.
        :returns: The document as a list of HTML blocks.
        """
        
        try:
            r = requests.get(url=self.server_path + '/json-html/{}'.format(document_id))
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        r.encoding = 'utf-8'
        self.__raiseExceptionIfDocumentNotFound(r)
        return r.json()
    
    @contract
    def getDocumentFullText(self, document_id : 'int') -> 'str':
        """Gets the full text of a document.
        
        :param document_id: The id of the document whose text will be fetched.
        :returns: The text of the document.
        """
        
        try:
            r = requests.get(url=self.server_path + '/{}'.format(document_id))
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        r.encoding = 'utf-8'
        self.__raiseExceptionIfBlockNotFound(r)
        return r.text
    
    @contract
    def loadDocument(self, document_id : 'int', content : 'bytes') -> 'bool':
        """Loads a new document to Ephemeral.
        
        :param document_id: The id of the document.
        :param content: The content of the document.
        :returns: True if the document was successfully loaded, false otherwise.
        """
        
        try:
            r = requests.post(url=self.server_path + '/load/{}'.format(document_id), data=content)
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        return True
    
    @contract
    def modifyBlock(self, document_id : 'int', block_id : 'int', new_content: 'str') -> 'bool':
        """Modifies the specified block in the given document.
        
        :param document_id: The id of the document.
        :param block_id: The id of the block to be modified.
        :param new_content: The new content of the block.
        """

        try:
            r = requests.put(url=self.server_path + '/{}/{}'.format(document_id, block_id), data=bytes(new_content, encoding='utf-8'))
        except requests.exceptions.ConnectionError:
            raise EphemeralException('Cannot connect to Ephemeral.')
        r.encoding = 'utf-8'
        self.__raiseExceptionIfBlockNotFound(r)
        
        return True
