__all__ = ["HeaderData", "MessageFlags", "ScopedPDU", "SNMPv3Message"]

import threading
import weakref

from snmp.ber import *
from snmp.exception import *
from snmp.message import *
from snmp.pdu import *
from snmp.security import *
from snmp.security.levels import *
from snmp.types import *
from snmp.typing import *
from snmp.utils import *

pduTypes = {
    cls.TYPE: cls for cls in cast(Tuple[Type[AnyPDU], ...], (
        GetRequestPDU,
        GetNextRequestPDU,
        ResponsePDU,
        SetRequestPDU,
        GetBulkRequestPDU,
        InformRequestPDU,
        SNMPv2TrapPDU,
        ReportPDU,
    ))
}

class InvalidMessage(IncomingMessageError):
    pass

class LateResponse(IncomingMessageError):
    pass

class ResponseMismatch(IncomingMessageError):
    @classmethod
    def byField(cls, field: str) -> "ResponseMismatch":
        return cls(f"{field} does not match request")

class UnknownSecurityModel(IncomingMessageError):
    pass

@final
class MessageFlags(OctetString):
    MIN_SIZE = 1

    AUTH_FLAG: ClassVar[int]        = (1 << 0)
    PRIV_FLAG: ClassVar[int]        = (1 << 1)
    REPORTABLE_FLAG: ClassVar[int]  = (1 << 2)

    def __init__(self,
        securityLevel: SecurityLevel = noAuthNoPriv,
        reportable: bool = False,
    ) -> None:
        self.securityLevel = securityLevel
        self.reportableFlag = reportable

    def __repr__(self) -> str:
        return f"{typename(self)}({self.securityLevel}, {self.reportableFlag})"

    def __str__(self) -> str:
        return self.toString()

    def toString(self, depth: int = 0, tab: str = "    ") -> str:
        indent = tab * depth
        subindent = indent + tab

        return "\n".join((
            f"{indent}{typename(self)}:",
            f"{subindent}Security Level: {self.securityLevel}",
            f"{subindent}Reportable: {self.reportableFlag}",
        ))

    @classmethod
    def interpret(cls, data: Asn1Data = b"") -> "MessageFlags":
        byte = data[0]
        securityLevel = SecurityLevel(
            byte & cls.AUTH_FLAG,
            byte & cls.PRIV_FLAG,
        )

        reportable = (byte & cls.REPORTABLE_FLAG != 0)
        return cls(securityLevel, reportable)

    @property
    def data(self) -> bytes:
        byte = 0

        if self.authFlag:
            byte |= self.AUTH_FLAG

        if self.privFlag:
            byte |= self.PRIV_FLAG

        if self.reportableFlag:
            byte |= self.REPORTABLE_FLAG

        return bytes((byte,))

    @property
    def authFlag(self) -> bool:
        return self.securityLevel.auth

    @authFlag.setter
    def authFlag(self, value: Any) -> None:
        auth = bool(value)
        if auth != self.securityLevel.auth:
            self.securityLevel = SecurityLevel(
                auth,
                self.securityLevel.priv,
            )

    @property
    def privFlag(self) -> bool:
        return self.securityLevel.priv

    @privFlag.setter
    def privFlag(self, value: Any) -> None:
        priv = bool(value)
        if priv != self.securityLevel.priv:
            self.securityLevel = SecurityLevel(
                self.securityLevel.auth,
                priv,
            )

@final
class HeaderData(Sequence):
    def __init__(self,
        msgID: int,
        maxSize: int,
        flags: MessageFlags,
        securityModel: SecurityModel,
    ) -> None:
        self.id = msgID
        self.maxSize = maxSize
        self.flags = flags
        self.securityModel = securityModel

    def __iter__(self) -> Iterator[Asn1Encodable]:
        yield Integer(self.id)
        yield Integer(self.maxSize)
        yield self.flags
        yield Integer(self.securityModel)

    def __len__(self) -> int:
        return 4

    def __repr__(self) -> str:
        args = (
            str(self.id),
            str(self.maxSize),
            repr(self.flags),
            str(SecurityModel(self.securityModel)),
        )

        return f"{typename(self)}({', '.join(args)})"

    def __str__(self) -> str:
        return self.toString()

    def toString(self, depth: int = 0, tab: str = "    ") -> str:
        indent = tab * depth
        subindent = indent + tab
        securityModel = SecurityModel(self.securityModel)

        return "\n".join((
            f"{indent}{typename(self)}:",
            f"{subindent}Message ID: {self.id}",
            f"{subindent}Sender Message Size Limit: {self.maxSize}",
            f"{self.flags.toString(depth+1, tab)}",
            f"{subindent}Security Model: {securityModel.name}"
        ))

    @classmethod
    def deserialize(cls, data: Asn1Data) -> "HeaderData":
        msgID,      data = Integer      .decode(data, leftovers=True)
        msgMaxSize, data = Integer      .decode(data, leftovers=True)
        msgFlags,   data = MessageFlags .decode(data, leftovers=True)
        msgSecurityModel = Integer      .decode(data)

        if msgID.value < 0:
            raise ParseError("msgID may not be less than 0")
        elif msgMaxSize.value < 484:
            raise ParseError("msgMaxSize may not be less than 484")
        elif msgSecurityModel.value < 1:
            raise ParseError("msgSecurityModel may not be less than 1")

        try:
            securityModel = SecurityModel(msgSecurityModel.value)
        except ValueError as err:
            raise UnknownSecurityModel(msgSecurityModel.value) from err

        return cls(
            msgID.value,
            msgMaxSize.value,
            msgFlags,
            securityModel,
        )

@final
class ScopedPDU(Sequence):
    def __init__(self,
        pdu: AnyPDU,
        contextEngineID: bytes,
        contextName: bytes = b"",
    ) -> None:
        self.contextEngineID = contextEngineID
        self.contextName = contextName
        self.pdu = pdu

    def __iter__(self) -> Iterator[Asn1Encodable]:
        yield OctetString(self.contextEngineID)
        yield OctetString(self.contextName)
        yield self.pdu

    def __len__(self) -> int:
        return 3

    def __repr__(self) -> str:
        args = (
            repr(self.pdu),
            repr(self.contextEngineID),
            f"contextName={repr(self.contextName)}"
        )

        return f"{typename(self)}({', '.join(args)})"

    def __str__(self) -> str:
        return self.toString()

    def toString(self, depth: int = 0, tab: str = "    ") -> str:
        indent = tab * depth
        subindent = indent + tab
        return "\n".join((
            f"{indent}{typename(self)}:",
            f"{subindent}Context Engine ID: {self.contextEngineID!r}",
            f"{subindent}Context Name: {self.contextName!r}",
            f"{self.pdu.toString(depth=depth+1, tab=tab)}"
        ))

    @classmethod
    def deserialize(cls,
        data: Asn1Data,
        types: Optional[Mapping[Identifier, Type[AnyPDU]]] = None,
    ) -> "ScopedPDU":
        if types is None:
            types = dict()

        contextEngineID, data = OctetString.decode(data, leftovers=True)
        contextName,     data = OctetString.decode(data, leftovers=True)
        identifier = Identifier.decode(subbytes(data))

        try:
            pduType = types[identifier]
        except KeyError as err:
            raise ParseError(f"Invalid PDU type: {identifier}") from err

        return cls(
            pduType.decode(data),
            contextEngineID = cast(bytes, contextEngineID.data),
            contextName     = cast(bytes, contextName.data),
        )

class SNMPv3Message(Sequence):
    VERSION = MessageProcessingModel.SNMPv3

    def __init__(self,
        header: HeaderData,
        scopedPDU: Optional[ScopedPDU] = None,
        encryptedPDU: Optional[OctetString] = None,
        securityParameters: Optional[OctetString] = None,
    ) -> None:
        if securityParameters is None:
            securityParameters = OctetString()

        self.header = header
        self.securityParameters = securityParameters
        self.scopedPDU = scopedPDU
        self.encryptedPDU = encryptedPDU

    def __iter__(self) -> Iterator[Asn1Encodable]:
        yield Integer(self.VERSION)
        yield self.header
        yield self.securityParameters

        if self.header.flags.privFlag:
            yield self.encryptedPDU
        else:
            yield self.scopedPDU

    def __len__(self) -> int:
        return 4;

    def __repr__(self) -> str:
        args = [repr(self.header)]

        if self.header.flags.privFlag:
            args.append(f"encryptedPDU={repr(self.encryptedPDU)}")
        else:
            args.append(f"scopedPDU={repr(self.scopedPDU)}")

        args.append(f"securityParameters={repr(self.securityParameters)}")

        return f"{typename(self)}({', '.join(args)})"

    def __str__(self) -> str:
        return self.toString()

    def toString(self, depth: int = 0, tab: str = "    ") -> str:
        indent = tab * depth
        subindent = indent + tab

        if self.header.flags.privFlag:
            payload = f"{subindent}Encrypted Data: {self.encryptedPDU}"
        else:
            payload = self.scopedPDU.toString(depth+1, tab)

        return "\n".join((
            f"{indent}{typename(self)}:",
            f"{self.header.toString(depth+1, tab)}",
            f"{subindent}Security Parameters: {self.securityParameters}",
            payload,
        ))

    @classmethod
    def decode(cls, data, leftovers=False, copy=False, **kwargs):
        return super().decode(data, leftovers, copy, **kwargs)

    @classmethod
    def deserialize(cls, data: Asn1Data):
        msgVersion, ptr = Integer.decode(data, leftovers=True)

        try:
            version = MessageProcessingModel(msgVersion.value)
        except ValueError as err:
            raise BadVersion(msgVersion.value) from err

        if version != cls.VERSION:
            raise BadVersion(f"{typename} does not support {version.name}")

        msgGlobalData, ptr = HeaderData.decode(ptr, leftovers=True)
        msgSecurityData, ptr = OctetString.decode(ptr, True, copy=False)

        scopedPDU = None
        encryptedPDU = None
        if msgGlobalData.flags.privFlag:
            encryptedPDU = OctetString.decode(ptr)
        else:
            scopedPDU = ScopedPDU.decode(ptr, types=pduTypes)

        return cls(
            msgGlobalData,
            scopedPDU=scopedPDU,
            encryptedPDU=encryptedPDU,
            securityParameters=msgSecurityData,
        )

    @property
    def plaintext(self) -> bytes:
        return self.scopedPDU.encode()

    @plaintext.setter
    def plaintext(self, data: bytes) -> None:
        self.scopedPDU, _ = ScopedPDU.decode(
            data,
            leftovers=True,
            types=pduTypes,
        )

class OldSNMPv3Message:
    def __init__(self,
        msgID: int,
        securityLevel: SecurityLevel,
        securityParameters: SecurityParameters,
        data: ScopedPDU,
    ):
        self.id = msgID
        self.securityLevel = securityLevel
        self.securityEngineID = securityParameters.securityEngineID
        self.securityName = securityParameters.securityName
        self.data = data

    def __repr__(self) -> str:
        args = (repr(member) for member in (
            self.id,
            self.securityLevel,
            SecurityParameters(self.securityEngineID, self.securityName),
            self.data,
        ))

        return f"{typename(self)}({', '.join(args)})"

    def __str__(self) -> str:
        return self.toString()

    def toString(self, depth: int = 0, tab: str = "    ") -> str:
        indent = tab * depth
        subindent = indent + tab
        return "\n".join((
            f"{indent}{typename(self)}:",
            f"{subindent}Message ID: {self.id}",
            f"{subindent}Security Engine ID: {self.securityEngineID!r}",
            f"{subindent}Security Level: {self.securityLevel}",
            f"{subindent}Security Name: {self.securityName!r}",
            f"{self.data.toString(depth+1, tab)}",
        ))

class CacheEntry:
    def __init__(self,
        engineID: bytes,
        contextName: bytes,
        handle: RequestHandle[OldSNMPv3Message],
        securityName: bytes,
        securityModel: SecurityModel,
        securityLevel: SecurityLevel,
    ):
        self.context = contextName
        self.engineID = engineID
        self.handle = weakref.ref(handle)
        self.securityName = securityName
        self.securityModel = securityModel
        self.securityLevel = securityLevel

class SNMPv3MessageProcessor(MessageProcessor[OldSNMPv3Message, AnyPDU]):
    VERSION = MessageProcessingModel.SNMPv3

    def __init__(self) -> None:
        self.cacheLock = threading.Lock()
        self.generator = self.newGenerator()
        self.outstanding: Dict[int, CacheEntry] = {}

        self.securityLock = threading.Lock()
        self.defaultSecurityModel: Optional[SecurityModel] = None
        self.securityModules: Dict[SecurityModel, SecurityModule] = {}

    @staticmethod
    def newGenerator() -> NumberGenerator:
        return NumberGenerator(31, signed=False)

    def cache(self, entry: CacheEntry) -> int:
        retry = 0
        while retry < 10:
            with self.cacheLock:
                msgID = next(self.generator)
                if msgID == 0:
                    self.generator = self.newGenerator()
                elif msgID not in self.outstanding:
                    self.outstanding[msgID] = entry
                    return msgID

            retry += 1

        raise Exception("Failed to allocate message ID")

    def retrieve(self, msgID: int) -> CacheEntry:
        with self.cacheLock:
            return self.outstanding[msgID]

    def uncache(self, msgID: int) -> None:
        with self.cacheLock:
            try:
                del self.outstanding[msgID]
            except KeyError:
                pass

    def addSecurityModuleIfNeeded(self,
        module: SecurityModule,
        default: bool = False,
    ) -> None:
        with self.securityLock:
            if module.MODEL not in self.securityModules:
                self.securityModules[module.MODEL] = module

                if default or self.defaultSecurityModel is None:
                    self.defaultSecurityModel = module.MODEL

    def prepareDataElements(self,
        msg: Asn1Data,
    ) -> Tuple[OldSNMPv3Message, RequestHandle[OldSNMPv3Message]]:
        msg = decode(msg, expected=SEQUENCE, copy=False)
        msgVersion, msg = Integer.decode(msg, leftovers=True)

        if msgVersion.value != MessageProcessingModel.SNMPv3:
            ver = MessageProcessingModel(msgVersion.value)
            raise BadVersion(f"{typename(self)} does not support {ver.name}")

        msgGlobalData, msg = HeaderData.decode(msg, leftovers=True)

        with self.securityLock:
            try:
                securityModule = self.securityModules[
                    msgGlobalData.securityModel
                ]
            except KeyError as e:
                raise UnknownSecurityModel(msgGlobalData.securityModel) from e

        try:
            securityLevel = SecurityLevel(
                auth=msgGlobalData.flags.authFlag,
                priv=msgGlobalData.flags.privFlag)
        except ValueError as err:
            raise InvalidMessage(f"Invalid msgFlags: {err}") from err

        security, data = securityModule.processIncoming(msg, securityLevel)
        scopedPDU, _ = ScopedPDU.decode(data, types=pduTypes, leftovers=True)

        if isinstance(scopedPDU.pdu, Response):
            try:
                entry = self.retrieve(msgGlobalData.id)
            except KeyError as err:
                errmsg = f"Unknown msgID: {msgGlobalData.id}"
                raise ResponseMismatch(errmsg) from err

            handle = entry.handle()
            if handle is None:
                raise LateResponse("Handle has already been released")

            report = isinstance(scopedPDU.pdu, Internal)
            if not report and entry.securityLevel < securityLevel:
                raise ResponseMismatch.byField("Security Level")

            if not report and entry.engineID != security.securityEngineID:
                raise ResponseMismatch.byField("Security Engine ID")

            if entry.securityName != security.securityName:
                raise ResponseMismatch.byField("Security Name")

            if not report and entry.engineID != scopedPDU.contextEngineID:
                raise ResponseMismatch.byField("Context Engine ID")

            if entry.context != scopedPDU.contextName:
                raise ResponseMismatch.byField("Context Name")
        else:
            raise UnsupportedFeature("Received a non-response PDU type")

        message = \
            OldSNMPv3Message(msgGlobalData.id, securityLevel, security, scopedPDU)
        return message, handle

    def prepareOutgoingMessage(self,    # type: ignore[override]
        pdu: AnyPDU,
        handle: RequestHandle[OldSNMPv3Message],
        engineID: bytes,
        securityName: bytes,
        securityLevel: SecurityLevel = noAuthNoPriv,
        securityModel: Optional[SecurityModel] = None,
        contextName: bytes = b"",
    ) -> bytes:

        with self.securityLock:
            if securityModel is None:
                assert self.defaultSecurityModel is not None
                securityModel = self.defaultSecurityModel

            try:
                securityModule = self.securityModules[securityModel]
            except KeyError as err:
                errmsg = f"Security Model {securityModel} has not been enabled"
                raise ValueError(errmsg) from err

        entry = CacheEntry(
            engineID,
            contextName,
            handle,
            securityName,
            securityModel,
            securityLevel)

        msgID = self.cache(entry)
        handle.addCallback(self.uncache, msgID)

        flags = MessageFlags(securityLevel, isinstance(pdu, Confirmed))
        header = HeaderData(msgID, 1472, flags, securityModel)
        scopedPDU = ScopedPDU(pdu, engineID, contextName=contextName)
        message = SNMPv3Message(header, scopedPDU)

        return securityModule.prepareOutgoing(message, engineID, securityName)
