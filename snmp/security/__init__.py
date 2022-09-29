__all__ = [
    "SecurityLevel", "SecurityModel", "SecurityModule", "SecurityParameters",
]

from abc import abstractmethod
import enum

from snmp.utils import typename

class SecurityLevel:
    def __init__(self, auth=False, priv=False):
        self._auth = False
        self._priv = False

        self.auth = auth
        self.priv = priv

    def __repr__(self):
        return "{}(auth={}, priv={})".format(
            typename(self),
            self.auth,
            self.priv
        )

    def __str__(self):
        return "{}{}".format(
            "auth" if self.auth else "noAuth",
            "Priv" if self.priv else "NoPriv"
        )

    @property
    def auth(self):
        return self._auth

    @property
    def priv(self):
        return self._priv

    @auth.setter
    def auth(self, value):
        _value = bool(value)
        if not _value and self.priv:
            msg = "Cannot disable authentication while privacy is enabled"
            raise ValueError(msg)

        self._auth = _value

    @priv.setter
    def priv(self, value):
        _value = bool(value)
        if _value and not self.auth:
            msg = "Cannot enable privacy while authentication is disabled"
            raise ValueError(msg)

        self._priv = _value

    def __eq__(self, other):
        try:
            return self.auth == other.auth and self.priv == other.priv
        except AttributeError:
            return NotImplemented

    def __lt__(self, other):
        if self.auth:
            return other.priv and not self.priv
        else:
            return other.auth

    def __ge__(self, other):
        return not self < other

class SecurityModel(enum.IntEnum):
    USM = 3

class SecurityParameters:
    def __init__(self, engineID, userName):
        self.securityEngineID = engineID
        self.securityName = userName

    def __repr__(self):
        return f"{typename(self)}({self.securityEngineID}, {self.securityName})"

class SecurityModule:
    @abstractmethod
    def processIncoming(self, msg, securityLevel, timestamp=None):
        ...

    @abstractmethod
    def prepareOutgoing(self, header, data, engineID,
                            securityName, securityLevel):
        ...
