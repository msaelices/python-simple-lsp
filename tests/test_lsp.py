import logging
from io import IOBase
from mdcompletion.doc import Document
from mdcompletion.jsonrpc import Message, decode_msg
from mdcompletion.lsp import LspConsumer


class FakeStream(IOBase):
    def __init__(self) -> None:
        self.messages = []

    def write(self, s: str) -> int:
        self.messages.append(decode_msg(s.encode()))
        return len(s)


def test_initialize():
    stream = FakeStream()
    logger = logging.getLogger('dummy')
    logger.addHandler(logging.NullHandler())
    msg = Message(
        {
            'method': 'initialize',
            'params': {
                'rootPath': None,
                'clientInfo': {
                    'name': 'Neovim',
                    'version': '0.9.4',
                },
                'trace': 'off',
                'capabilities': {},
                'workspaceFolders': None,
                'processId': 1234,
                'rootUri': None,
            },
            'jsonrpc': '2.0',
            'id': 1,
        }
    )
    consumer = LspConsumer(stream=stream, logger=logger)
    consumer.consume(msg)
    assert stream.messages == [
        Message(
            {
                'id': 1,
                'jsonrpc': '2.0',
                'result': {
                    'capabilities': {
                        'codeActionProvider': False,
                        'codeLensProvider': {'resolveProvider': False},
                        'completionProvider': {
                            'resolveProvider': True,
                            'triggerCharacters': [']'],
                        },
                        'definitionProvider': False,
                        'documentFormattingProvider': False,
                        'documentHighlightProvider': False,
                        'documentRangeFormattingProvider': False,
                        'documentSymbolProvider': False,
                        'executeCommandProvider': {'commands': []},
                        'foldingRangeProvider': False,
                        'hoverProvider': False,
                        'referencesProvider': False,
                        'renameProvider': False,
                        'signatureHelpProvider': {'triggerCharacters': ['(', ',', '=']},
                        'textDocumentSync': {'change': 1, 'openClose': True},
                        'workspace': {'workspaceFolders': {'changeNotifications': False, 'supported': False}},
                    },
                    'serverInfo': {'name': 'mdcompletion'},
                },
            }
        )
    ]


def test_did_open():
    stream = FakeStream()
    logger = logging.getLogger('dummy')
    logger.addHandler(logging.NullHandler())
    msg = Message(
        {
            'method': 'textDocument/didOpen',
            'params': {
                'textDocument': {
                    'uri': 'file:///tmp/test.md',
                    'languageId': 'markdown',
                    'version': 1,
                    'text': 'Hello world!',
                },
            },
            'jsonrpc': '2.0',
            'id': 1,
        }
    )
    consumer = LspConsumer(stream=stream, logger=logger)
    consumer.consume(msg)
    assert consumer.documents == {
        'file:///tmp/test.md': Document(
            uri='file:///tmp/test.md',
            text='Hello world!',
        ),
    }


def test_did_change():
    stream = FakeStream()
    logger = logging.getLogger('dummy')
    logger.addHandler(logging.NullHandler())
    msg = Message(
        {
            'method': 'textDocument/didChange',
            'params': {
                'textDocument': {
                    'uri': 'file:///tmp/test.md',
                    'version': 2,
                },
                'contentChanges': [
                    {
                        'range': {'start': {'line': 0, 'character': 0}, 'end': {'line': 0, 'character': 0}},
                        'rangeLength': 0,
                        'text': 'Bye world!',
                    },
                ],
            },
            'jsonrpc': '2.0',
            'id': 1,
        }
    )
    consumer = LspConsumer(stream=stream, logger=logger)
    consumer.documents = {
        'file:///tmp/test.md': Document(
            uri='file:///tmp/test.md',
            text='Hello world!',
        ),
    }
    consumer.consume(msg)
    assert consumer.documents == {
        'file:///tmp/test.md': Document(
            uri='file:///tmp/test.md',
            text='Bye world!',
        ),
    }
    assert stream.messages == []


def test_completion():
    stream = FakeStream()
    logger = logging.getLogger('dummy')
    logger.addHandler(logging.NullHandler())
    msg = Message(
        {
            'method': 'textDocument/completion',
            'params': {
                'context': {'triggerCharacter': ']', 'triggerKind': 2},
                'position': {
                    'line': 0,
                    'character': 13,
                },
                'textDocument': {
                    'uri': 'file:///tmp/test.md',
                },
            },
            'jsonrpc': '2.0',
            'id': 1,
        }
    )
    consumer = LspConsumer(stream=stream, logger=logger, github_url='https://github.com/foo/bar')
    consumer.documents = {
        'file:///tmp/test.md': Document(
            uri='file:///tmp/test.md',
            text='Link to [PR1]',
        ),
    }
    consumer.consume(msg)
    assert stream.messages == [
        Message(
            {
                'jsonrpc': '2.0',
                'id': 1,
                'result': {
                    'isIncomplete': False,
                    'items': [
                        {
                            'label': 'PR #1 link',
                            'kind': 18,
                            'insertText': '(https://github.com/foo/bar/pull/1)',
                        },
                    ],
                },
            }
        )
    ]
