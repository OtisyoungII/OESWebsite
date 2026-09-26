"""Windows Credential Manager storage; secret values are never logged or returned in errors."""
import ctypes
import re
from ctypes import wintypes

TARGET = 'OES Core/Outbound Worker'
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2


class CREDENTIALW(ctypes.Structure):
    _fields_ = [('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
                ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
                ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
                ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)),
                ('Persist', wintypes.DWORD), ('AttributeCount', wintypes.DWORD),
                ('Attributes', wintypes.LPVOID), ('TargetAlias', wintypes.LPWSTR),
                ('UserName', wintypes.LPWSTR)]


class WindowsCredentialStore:
    def __init__(self, advapi=None):
        if advapi is None:
            if not hasattr(ctypes, 'WinDLL'):
                raise RuntimeError('Windows Credential Manager is unavailable')
            advapi = ctypes.WinDLL('Advapi32.dll', use_last_error=True)
        self.api = advapi
        if hasattr(self.api.CredReadW, 'argtypes'):
            self.api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                                           wintypes.DWORD,
                                           ctypes.POINTER(ctypes.POINTER(CREDENTIALW))]
            self.api.CredReadW.restype = wintypes.BOOL
            self.api.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
            self.api.CredWriteW.restype = wintypes.BOOL
            self.api.CredFree.argtypes = [ctypes.c_void_p]
            self.api.CredFree.restype = None

    def read(self):
        pointer = ctypes.POINTER(CREDENTIALW)()
        if not self.api.CredReadW(TARGET, CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
            return None
        try:
            item = pointer.contents
            raw = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
            value = raw.decode('ascii')
            return value if re.fullmatch(r'[0-9a-f]{64}', value) else None
        finally:
            self.api.CredFree(pointer)

    def write(self, secret, worker_id):
        if not re.fullmatch(r'[0-9a-f]{64}', secret or ''):
            raise ValueError('Secret must be 64 lowercase hexadecimal characters')
        blob = secret.encode('ascii')
        buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        credential = CREDENTIALW(Type=CRED_TYPE_GENERIC, TargetName=TARGET,
                                 Comment='OES outbound worker credential',
                                 CredentialBlobSize=len(blob), CredentialBlob=buffer,
                                 Persist=CRED_PERSIST_LOCAL_MACHINE, UserName=worker_id)
        if not self.api.CredWriteW(ctypes.byref(credential), 0):
            raise OSError('Windows Credential Manager rejected the credential')
