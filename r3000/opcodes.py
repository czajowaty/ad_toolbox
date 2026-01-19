import abc
import ctypes
import typing
from collections.abc import Callable
import dataclasses
from typing import ClassVar
from r3000 import registers
from r3000.registers import Register, ExecutionContext


EncodedInstruction = int
OpcodeDecoder = Callable[[EncodedInstruction], 'Instruction']


@dataclasses.dataclass
class OpcodeArgs:
    rs: Register | None = None
    rt: Register | None = None
    rd: Register | None = None
    imm: int | None = None

    def __str__(self) -> str:
        return f'rs={self.rs}, rt={self.rt}, rd={self.rd}, imm={self._imm_to_string()}'

    def _imm_to_string(self) -> str:
        return f'{self.imm:X}' if self.imm is not None else f'{None}'


class Helpers:
    @staticmethod
    def decode_rs(encoded: EncodedInstruction) -> Register:
        return registers.cpu_by_index[(encoded & 0x3e00000) >> 21]

    @staticmethod
    def encode_rs(args: OpcodeArgs) -> int:
        return args.rs.index << 21

    @staticmethod
    def decode_rt(encoded: EncodedInstruction) -> Register:
        return registers.cpu_by_index[Helpers.decode_rt_index(encoded)]

    @staticmethod
    def decode_rt_index(encoded: EncodedInstruction) -> int:
        return (encoded & 0x1f0000) >> 16

    @staticmethod
    def encode_rt(args: OpcodeArgs) -> int:
        return args.rt.index << 16

    @staticmethod
    def decode_rd(encoded: EncodedInstruction) -> Register:
        return registers.cpu_by_index[Helpers.decode_rd_index(encoded)]

    @staticmethod
    def decode_rd_index(encoded: EncodedInstruction) -> int:
        return (encoded & 0xf800) >> 11

    @staticmethod
    def encode_rd(args: OpcodeArgs) -> int:
        return args.rd.index << 11

    @staticmethod
    def decode_s_imm16(encoded: EncodedInstruction) -> int:
        return ctypes.c_int16(encoded).value

    @staticmethod
    def decode_u_imm16(encoded: EncodedInstruction) -> int:
        return encoded & 0xffff

    @staticmethod
    def encode_imm16(args: OpcodeArgs) -> int:
        return ctypes.c_uint16(args.imm).value

    @staticmethod
    def branch_address_string(context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'0x{Helpers.branch_address(context, args):08X}'

    @staticmethod
    def branch_address(context: ExecutionContext, args: OpcodeArgs) -> int:
        return context.pc.value + 4 + args.imm * 4

    @staticmethod
    def signed_imm_string(args: OpcodeArgs) -> str:
        return f'0x{args.imm:X}' if args.imm >= 0 else f'-0x{-args.imm:X}'

    @staticmethod
    def unsigned_imm_string(args: OpcodeArgs) -> str:
        return f'0x{args.imm:X}'


@dataclasses.dataclass
class Opcode(abc.ABC):
    name: str
    primary_opcode: int
    args_number: int

    def to_string(self, context: ExecutionContext, args: OpcodeArgs) -> str:
        args_string = self.args_to_string(context, args)
        if args_string is None:
            return ''
        return f'{self.name} {args_string}' if len(args_string) > 0 else self.name

    def encode(self, args: OpcodeArgs) -> EncodedInstruction:
        return (self.primary_opcode << 26) | self.encode_args(args)

    @staticmethod
    def decode_primary(encoded) -> int:
        return (encoded & 0xfc000000) >> 26

    @classmethod
    @abc.abstractmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str: ...

    @classmethod
    @abc.abstractmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs: ...

    @classmethod
    @abc.abstractmethod
    def encode_args(cls, args: OpcodeArgs) -> int: ...


def _primary_opcode_mixin(primary: int):
    @dataclasses.dataclass
    class _PrimaryOpcodeMixin:
        PRIMARY_OPCODE: ClassVar[int] = primary
        primary_opcode: int = dataclasses.field(init=False, default=PRIMARY_OPCODE)

    return _PrimaryOpcodeMixin


@dataclasses.dataclass
class InvalidOpcode(Opcode):
    name: str = dataclasses.field(init=False, default='invalid')
    primary_opcode: int = dataclasses.field(init=False, default=0)
    args_number: int = dataclasses.field(init=False, default=0)
    encoded: EncodedInstruction
    cause: str

    def __post_init__(self):
        self.primary_opcode = self.decode_primary(self.encoded)

    def encode(self, args: OpcodeArgs = None) -> EncodedInstruction:
        return self.encoded

    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return ''

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs()

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return 0


@dataclasses.dataclass
class _OneArgMixin:
    args_number: int = dataclasses.field(init=False, default=1)


@dataclasses.dataclass
class _TwoArgsMixin:
    args_number: int = dataclasses.field(init=False, default=2)


@dataclasses.dataclass
class _ThreeArgsMixin:
    args_number: int = dataclasses.field(init=False, default=3)


@dataclasses.dataclass
class SecondaryOpcode(_primary_opcode_mixin(0x00), Opcode, abc.ABC):
    secondary_opcode: int

    def encode(self, args: OpcodeArgs) -> EncodedInstruction:
        return super().encode(args) | self.encode_secondary()

    @classmethod
    def decode_secondary(cls, encoded: EncodedInstruction) -> int:
        return encoded & 0x3f

    def encode_secondary(self) -> int:
        return self.secondary_opcode


class _RsRtImm16EncoderMixin(_ThreeArgsMixin):
    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rs(args) | Helpers.encode_rt(args) | Helpers.encode_imm16(args)


class _RsRtImmS16CoderMixin(_RsRtImm16EncoderMixin):
    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(
            rs=Helpers.decode_rs(encoded),
            rt=Helpers.decode_rt(encoded),
            imm=Helpers.decode_s_imm16(encoded))


class _RsRtImmU16CoderMixin(_RsRtImm16EncoderMixin):
    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(
            rs=Helpers.decode_rs(encoded),
            rt=Helpers.decode_rt(encoded),
            imm=Helpers.decode_u_imm16(encoded))


class _LoadStoreArgsConverterMixin:
    @classmethod
    def args_to_string(cls, _context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rt}, {Helpers.signed_imm_string(args)}({args.rs})'


@dataclasses.dataclass
class _ShiftImmOpcode(_ThreeArgsMixin, SecondaryOpcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rd}, {args.rt}, {Helpers.unsigned_imm_string(args)}'

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(rt=Helpers.decode_rt(encoded), rd=Helpers.decode_rd(encoded), imm=(encoded & 0x7c0) >> 6)

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rt(args) | Helpers.encode_rd(args) | (args.imm << 6)


class _RsRtRdCoderMixin(_ThreeArgsMixin):
    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(rs=Helpers.decode_rs(encoded), rt=Helpers.decode_rt(encoded), rd=Helpers.decode_rd(encoded))

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rs(args) | Helpers.encode_rt(args) | Helpers.encode_rd(args)


@dataclasses.dataclass
class _RsRtRdOpcode(_RsRtRdCoderMixin, SecondaryOpcode, abc.ABC):
    pass


@dataclasses.dataclass
class _ShiftRegOpcode(_RsRtRdOpcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rd}, {args.rt}, {args.rs}'


@dataclasses.dataclass
class _JrOpcode(_OneArgMixin, SecondaryOpcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return str(args.rs)

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(rs=Helpers.decode_rs(encoded))

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rs(args)


@dataclasses.dataclass
class _JalrOpcode(_TwoArgsMixin, SecondaryOpcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rs}' if args.rd is registers.ra else f'{args.rs}, {args.rd}'

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(rs=Helpers.decode_rs(encoded), rd=Helpers.decode_rd(encoded))

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rs(args) | Helpers.encode_rd(args)


@dataclasses.dataclass
class _ExceptionOpcode(_OneArgMixin, SecondaryOpcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return Helpers.unsigned_imm_string(args) if args.imm != 0 else ''

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(imm=(encoded & 0x3ffffc0) >> 6)

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return args.imm << 6


@dataclasses.dataclass
class _MfOpcode(_OneArgMixin, SecondaryOpcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return str(args.rd)

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(rd=Helpers.decode_rd(encoded))

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rd(args)


@dataclasses.dataclass
class _MtOpcode(_OneArgMixin, SecondaryOpcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return str(args.rs)

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(rs=Helpers.decode_rs(encoded))

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rs(args)


@dataclasses.dataclass
class _MulDivOpcode(_TwoArgsMixin, SecondaryOpcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rs}, {args.rt}'

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(rs=Helpers.decode_rs(encoded), rt=Helpers.decode_rt(encoded))

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rs(args) | Helpers.encode_rt(args)


@dataclasses.dataclass
class _AluRegOpcode(_RsRtRdOpcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rd}, {args.rs}, {args.rt}'


@dataclasses.dataclass
class _JumpImmediateOpcode(_OneArgMixin, Opcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'0x{(context.pc.value & 0xf0000000) + args.imm * 4:08X}'

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(imm=encoded & 0x3ffffff)

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return args.imm


@dataclasses.dataclass
class _BranchZeroConditionOpcode(_TwoArgsMixin, Opcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rs}, {Helpers.branch_address_string(context, args)}'

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(rs=Helpers.decode_rs(encoded), imm=Helpers.decode_s_imm16(encoded))

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rs(args) | Helpers.encode_imm16(args)


@dataclasses.dataclass
class BranchZeroConditionWithDiscriminatorOpcode(_primary_opcode_mixin(0x01), _BranchZeroConditionOpcode):
    discriminator: int

    def encode(self, args: OpcodeArgs) -> int:
        return super().encode(args) | (self.discriminator << 16)

    @classmethod
    def decode_discriminator(cls, encoded: EncodedInstruction) -> int:
        return (encoded & 0x1f0000) >> 16


@dataclasses.dataclass
class _BranchNonZeroConditionOpcode(_RsRtImmS16CoderMixin, Opcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rs}, {args.rt}, {Helpers.branch_address_string(context, args)}'


@dataclasses.dataclass
class _AluSignedImmOpcode(_RsRtImmS16CoderMixin, Opcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rt}, {args.rs}, {Helpers.signed_imm_string(args)}'


@dataclasses.dataclass
class _AluUnsignedImmOpcode(_RsRtImmU16CoderMixin, Opcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rt}, {args.rs}, {Helpers.unsigned_imm_string(args)}'


@dataclasses.dataclass
class _LuiOpcode(_TwoArgsMixin, Opcode):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rt}, {Helpers.unsigned_imm_string(args)}'

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(rt=Helpers.decode_rt(encoded), imm=Helpers.decode_u_imm16(encoded))

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rt(args) | Helpers.encode_imm16(args)


@dataclasses.dataclass
class _CpuLoadStoreOpcode(_RsRtImmS16CoderMixin, _LoadStoreArgsConverterMixin, Opcode):
    pass


@dataclasses.dataclass
class _CopNonLoadStoreOpcodeBase(Opcode, abc.ABC):
    COP0_OPCODE: ClassVar[int] = 0x10
    COP1_OPCODE: ClassVar[int] = 0x11
    COP2_OPCODE: ClassVar[int] = 0x12
    COP3_OPCODE: ClassVar[int] = 0x13
    is_exec_command: bool

    def encode(self, args: OpcodeArgs) -> EncodedInstruction:
        return super().encode(args) | (0x2000000 if self.is_exec_command else 0)

    @staticmethod
    def decode_is_exec_command(encoded) -> bool:
        return (encoded & 0x2000000) != 0


def _is_exec_command_mixin(flag: bool):
    @dataclasses.dataclass
    class _IsExecCommandMixin:
        is_exec_command: bool = dataclasses.field(init=False, default=flag)

    return _IsExecCommandMixin


@dataclasses.dataclass
class _CopNonExecuteCommandOpcodeBase(_is_exec_command_mixin(False), _CopNonLoadStoreOpcodeBase, abc.ABC):
    discriminator: int

    def encode(self, args: OpcodeArgs) -> EncodedInstruction:
        return super().encode(args) | (self.discriminator << 21)

    @staticmethod
    def decode_discriminator(encoded) -> int:
        return (encoded & 0x1e00000) >> 21


@dataclasses.dataclass
class _CopGetSetRegisterOpcodeBase(_TwoArgsMixin, _CopNonExecuteCommandOpcodeBase, abc.ABC):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{args.rt}, {args.rd}'

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_rt(args) | Helpers.encode_rd(args)


@dataclasses.dataclass
class _CopBranchOpcodeBase(_OneArgMixin, _is_exec_command_mixin(False), _CopNonExecuteCommandOpcodeBase, abc.ABC):
    branch_type: int

    def encode(self, args: OpcodeArgs) -> EncodedInstruction:
        return super().encode(args) | (self.branch_type << 16)

    @staticmethod
    def decode_branch_type(encoded) -> int:
        return (encoded & 0x1f0000) >> 16

    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'{Helpers.branch_address_string(context, args)}'

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(imm=Helpers.decode_s_imm16(encoded))

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return Helpers.encode_imm16(args)


@dataclasses.dataclass
class _CopExecuteOpcodeBase(_OneArgMixin, _is_exec_command_mixin(True), _CopNonLoadStoreOpcodeBase):
    @classmethod
    def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
        return f'0x{args.imm:06X}'

    @classmethod
    def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
        return OpcodeArgs(imm=encoded & 0x1ffffff)

    @classmethod
    def encode_args(cls, args: OpcodeArgs) -> int:
        return args.imm


def _cop_mfc_opcode(cop_id: int):
    return _cop_get_set_register_opcode('mfc{}', cop_id, registers.cop_dat_by_index[cop_id])


def _cop_cfc_opcode(cop_id: int):
    return _cop_get_set_register_opcode('cfc{}', cop_id, registers.cop_cnt_by_index[cop_id])


def _cop_mtc_opcode(cop_id: int):
    return _cop_get_set_register_opcode('mtc{}', cop_id, registers.cop_dat_by_index[cop_id])


def _cop_ctc_opcode(cop_id: int):
    return _cop_get_set_register_opcode('ctc{}', cop_id, registers.cop_cnt_by_index[cop_id])


def _cop_bcf_opcode(cop_id: int):
    return _cop_branch_opcode('f', cop_id, type_=0b00000)


def _cop_bct_opcode(cop_id: int):
    return _cop_branch_opcode('t', cop_id, type_=0b00001)


def _cop_execute_opcode(cop_id: int):
    @dataclasses.dataclass
    class _CopExecuteOpcode(_cop_non_load_store_opcode('cop{}', cop_id, _CopExecuteOpcodeBase)):
        pass

    return _CopExecuteOpcode


def _cop_lwc_opcode(cop_id: int):
    return _cop_load_store_opcode('lwc{}', cop_id, primary=0x30)


def _cop_swc_opcode(cop_id: int):
    return _cop_load_store_opcode('swc{}', cop_id, primary=0x38)


def _cop_opcode_name_mixin(name_format: str, cop_id: int):
    @dataclasses.dataclass
    class _CopOpcodeNameMixin:
        name: str = dataclasses.field(init=False, default=name_format.format(cop_id))

    return _CopOpcodeNameMixin


def _cop_get_set_register_opcode(base_name: str, cop_id: int, cop_registers: list[Register]) -> type[_CopGetSetRegisterOpcodeBase]:
    @dataclasses.dataclass
    class _CopGetSetRegisterOpcode(_cop_non_load_store_opcode(base_name, cop_id, _CopGetSetRegisterOpcodeBase)):
        @classmethod
        def args_to_string(cls, context: ExecutionContext, args: OpcodeArgs) -> str:
            return f'{args.rt}, {args.rd}'

        @classmethod
        def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
            return OpcodeArgs(rt=Helpers.decode_rt(encoded), rd=cop_registers[Helpers.decode_rd_index(encoded)])

        @classmethod
        def encode_args(cls, args: OpcodeArgs) -> int:
            return Helpers.encode_rt(args) | Helpers.encode_rd(args)

    return _CopGetSetRegisterOpcode


def _cop_branch_opcode(suffix: str, cop_id: int, type_: int) -> type[_CopBranchOpcodeBase]:
    @dataclasses.dataclass
    class _CopBranchOpcode(_cop_non_load_store_opcode(f'bc{{}}{suffix}', cop_id, _CopBranchOpcodeBase)):
        branch_type: int = dataclasses.field(init=False, default=type_)

    return _CopBranchOpcode


def _cop_non_load_store_opcode[T](name_format: str, cop_id: int, base_class: type[T]) -> type[T]:
    @dataclasses.dataclass
    class _CopNonLoadStoreOpcode(
            _cop_opcode_mixin(name_format, cop_id, primary=_CopNonLoadStoreOpcodeBase.COP0_OPCODE),
            base_class,
            abc.ABC):
        pass

    return _CopNonLoadStoreOpcode


def _cop_load_store_opcode(base_name: str, cop_id: int, primary: int):
    @dataclasses.dataclass
    class _CopLoadStoreOpcode(
            _cop_opcode_mixin(base_name, cop_id, primary),
            _RsRtImm16EncoderMixin,
            _LoadStoreArgsConverterMixin,
            Opcode):
        @classmethod
        def decode_args(cls, encoded: EncodedInstruction) -> OpcodeArgs:
            return OpcodeArgs(
                rs=Helpers.decode_rs(encoded),
                rt=registers.cop_dat_by_index[cop_id][Helpers.decode_rt_index(encoded)],
                imm=Helpers.decode_s_imm16(encoded))

        pass

    return _CopLoadStoreOpcode


def _cop_opcode_mixin(name_format: str, cop_id_: int, primary: int) -> type:
    @dataclasses.dataclass
    class _CopOpcodeMixin(_cop_opcode_name_mixin(name_format, cop_id_), _primary_opcode_mixin(primary + cop_id_)):
        cop_id: int = cop_id_

    return _CopOpcodeMixin


_CopNonLoadStoreOpcodes = tuple[
    _CopNonLoadStoreOpcodeBase,
    _CopNonLoadStoreOpcodeBase,
    _CopNonLoadStoreOpcodeBase,
    _CopNonLoadStoreOpcodeBase
]


def _cop_opcodes[T](cop_opcode_type_creator: Callable[[int], type[T]], *args, **kwargs) -> tuple[T, T, T, T]:
    return cop_opcode_type_creator(0)(*args, **kwargs), \
        cop_opcode_type_creator(1)(*args, **kwargs), \
        cop_opcode_type_creator(2)(*args, **kwargs), \
        cop_opcode_type_creator(3)(*args, **kwargs)


class Opcodes:
    sll = _ShiftImmOpcode('sll', secondary_opcode=0x00)
    srl = _ShiftImmOpcode('srl', secondary_opcode=0x02)
    sra = _ShiftImmOpcode('sra', secondary_opcode=0x03)
    sllv = _ShiftRegOpcode('sllv', secondary_opcode=0x04)
    srlv = _ShiftRegOpcode('srlv', secondary_opcode=0x06)
    srav = _ShiftRegOpcode('srav', secondary_opcode=0x07)
    jr = _JrOpcode('jr', secondary_opcode=0x08)
    jalr = _JalrOpcode('jalr', secondary_opcode=0x09)
    syscall = _ExceptionOpcode('syscall', secondary_opcode=0x0c)
    break_ = _ExceptionOpcode('break', secondary_opcode=0x0d)
    mfhi = _MfOpcode('mfhi', secondary_opcode=0x10)
    mthi = _MtOpcode('mthi', secondary_opcode=0x11)
    mflo = _MfOpcode('mflo', secondary_opcode=0x12)
    mtlo = _MtOpcode('mtlo', secondary_opcode=0x13)
    mult = _MulDivOpcode('mult', secondary_opcode=0x18)
    multu = _MulDivOpcode('multu', secondary_opcode=0x19)
    div = _MulDivOpcode('div', secondary_opcode=0x1a)
    divu = _MulDivOpcode('divu', secondary_opcode=0x1b)
    add = _AluRegOpcode('add', secondary_opcode=0x20)
    addu = _AluRegOpcode('addu', secondary_opcode=0x21)
    sub = _AluRegOpcode('sub', secondary_opcode=0x22)
    subu = _AluRegOpcode('subu', secondary_opcode=0x23)
    and_ = _AluRegOpcode('and', secondary_opcode=0x24)
    or_ = _AluRegOpcode('or', secondary_opcode=0x25)
    xor = _AluRegOpcode('xor', secondary_opcode=0x26)
    nor = _AluRegOpcode('nor', secondary_opcode=0x27)
    slt = _AluRegOpcode('slt', secondary_opcode=0x2a)
    sltu = _AluRegOpcode('sltu', secondary_opcode=0x2b)
    bltz = BranchZeroConditionWithDiscriminatorOpcode('bltz', discriminator=0b00000)
    bgez = BranchZeroConditionWithDiscriminatorOpcode('bgez', discriminator=0b00001)
    bltzal = BranchZeroConditionWithDiscriminatorOpcode('bltzal', discriminator=0b10000)
    bgezal = BranchZeroConditionWithDiscriminatorOpcode('bgezal', discriminator=0b10001)
    j = _JumpImmediateOpcode('j', primary_opcode=0x02)
    jal = _JumpImmediateOpcode('jal', primary_opcode=0x03)
    beq = _BranchNonZeroConditionOpcode('beq', primary_opcode=0x04)
    bne = _BranchNonZeroConditionOpcode('bne', primary_opcode=0x05)
    blez = _BranchZeroConditionOpcode('blez', primary_opcode=0x06)
    bgtz = _BranchZeroConditionOpcode('bgtz', primary_opcode=0x07)
    addi = _AluSignedImmOpcode('addi', primary_opcode=0x08)
    addiu = _AluSignedImmOpcode('addiu', primary_opcode=0x09)
    slti = _AluSignedImmOpcode('slti', primary_opcode=0x0a)
    sltiu = _AluSignedImmOpcode('sltiu', primary_opcode=0x0b)
    andi = _AluUnsignedImmOpcode('andi', primary_opcode=0x0c)
    ori = _AluUnsignedImmOpcode('ori', primary_opcode=0x0d)
    xori = _AluUnsignedImmOpcode('xori', primary_opcode=0x0e)
    lui = _LuiOpcode('lui', primary_opcode=0x0f)
    mfc = _cop_opcodes(_cop_mfc_opcode, discriminator=0b0000)
    cfc = _cop_opcodes(_cop_cfc_opcode, discriminator=0b0010)
    mtc = _cop_opcodes(_cop_mtc_opcode, discriminator=0b0100)
    ctc = _cop_opcodes(_cop_ctc_opcode, discriminator=0b0110)
    bcf = _cop_opcodes(_cop_bcf_opcode, discriminator=0b1000)
    bct = _cop_opcodes(_cop_bct_opcode, discriminator=0b1000)
    cop = _cop_opcodes(_cop_execute_opcode)
    lwc = _cop_opcodes(_cop_lwc_opcode)
    swc = _cop_opcodes(_cop_swc_opcode)
    lb = _CpuLoadStoreOpcode('lb', primary_opcode=0x20)
    lh = _CpuLoadStoreOpcode('lh', primary_opcode=0x21)
    lwl = _CpuLoadStoreOpcode('lwl', primary_opcode=0x22)
    lw = _CpuLoadStoreOpcode('lw', primary_opcode=0x23)
    lbu = _CpuLoadStoreOpcode('lbu', primary_opcode=0x24)
    lhu = _CpuLoadStoreOpcode('lhu', primary_opcode=0x25)
    lwr = _CpuLoadStoreOpcode('lwr', primary_opcode=0x26)
    sb = _CpuLoadStoreOpcode('sb', primary_opcode=0x28)
    sh = _CpuLoadStoreOpcode('sh', primary_opcode=0x29)
    swl = _CpuLoadStoreOpcode('swl', primary_opcode=0x2a)
    sw = _CpuLoadStoreOpcode('sw', primary_opcode=0x2b)
    swr = _CpuLoadStoreOpcode('swr', primary_opcode=0x2e)


@dataclasses.dataclass
class Instruction:
    opcode: Opcode
    args: OpcodeArgs

    def to_string(self, context: ExecutionContext):
        return self.opcode.to_string(context, self.args)

    def encode(self) -> EncodedInstruction:
        return self.opcode.encode(self.args)

    def is_valid(self) -> bool:
        return not isinstance(self.opcode, InvalidOpcode)


@dataclasses.dataclass
class InvalidInstruction(Instruction):
    opcode: InvalidOpcode
    args: OpcodeArgs = dataclasses.field(init=False, default_factory=OpcodeArgs)


class Decoder:
    def __init__(self):
        self._primary_decoders: list[OpcodeDecoder | None] = [None] * 0x40
        self._branch_zero_condition_decoders: list[OpcodeDecoder | None] = [None] * 0x20
        self._secondary_decoders: list[OpcodeDecoder | None] = [None] * 0x40
        self._coprocessor_with_discriminator_decoders: list[list[OpcodeDecoder | None]] = \
            [[None] * 0x10, [None] * 0x10, [None] * 0x10, [None] * 0x10]
        self._primary_decoders[SecondaryOpcode.PRIMARY_OPCODE] = self._secondary_opcode_decoder
        self._primary_decoders[BranchZeroConditionWithDiscriminatorOpcode.PRIMARY_OPCODE] = \
            self._branch_zero_condition_with_discriminator_opcode_decoder
        self._insert_primary_opcode_decoders(
            Opcodes.j, Opcodes.jal,
            Opcodes.beq, Opcodes.bne, Opcodes.blez, Opcodes.bgtz,
            Opcodes.addiu, Opcodes.addi, Opcodes.slti, Opcodes.sltiu,
            Opcodes.andi, Opcodes.ori, Opcodes.xori, Opcodes.lui,
            Opcodes.lb, Opcodes.lh, Opcodes.lwl, Opcodes.lw, Opcodes.lbu, Opcodes.lhu, Opcodes.lwr,
            Opcodes.sb, Opcodes.sh, Opcodes.swl, Opcodes.sw, Opcodes.swr)
        self._insert_secondary_opcode_decoders(
            Opcodes.sll, Opcodes.srl, Opcodes.sra, Opcodes.sllv, Opcodes.srlv, Opcodes.srav,
            Opcodes.jr, Opcodes.jalr, Opcodes.syscall, Opcodes.break_,
            Opcodes.mfhi, Opcodes.mthi, Opcodes.mflo, Opcodes.mtlo,
            Opcodes.mult, Opcodes.multu, Opcodes.div, Opcodes.divu,
            Opcodes.add, Opcodes.addu, Opcodes.sub, Opcodes.subu, Opcodes.and_, Opcodes.or_, Opcodes.xor, Opcodes.nor,
            Opcodes.slt, Opcodes.sltu)
        self._insert_zero_condition_decoders(Opcodes.bltz, Opcodes.bgez, Opcodes.bltzal, Opcodes.bgezal)
        self._primary_decoders[_CopNonLoadStoreOpcodeBase.COP0_OPCODE] = \
            lambda encoded: self._cop_non_load_store_decoder(encoded, cop_id=0)
        self._primary_decoders[_CopNonLoadStoreOpcodeBase.COP1_OPCODE] = \
            lambda encoded: self._cop_non_load_store_decoder(encoded, cop_id=1)
        self._primary_decoders[_CopNonLoadStoreOpcodeBase.COP2_OPCODE] = \
            lambda encoded: self._cop_non_load_store_decoder(encoded, cop_id=2)
        self._primary_decoders[_CopNonLoadStoreOpcodeBase.COP3_OPCODE] = \
            lambda encoded: self._cop_non_load_store_decoder(encoded, cop_id=3)
        self._insert_coprocessor_with_discriminator_decoders(Opcodes.mfc, Opcodes.cfc, Opcodes.mtc, Opcodes.ctc)
        self._coprocessor_with_discriminator_decoders[0][Opcodes.bcf[0].discriminator] = \
            lambda encoded: self._cop_branch_decoder(encoded, 0)
        self._coprocessor_with_discriminator_decoders[1][Opcodes.bcf[1].discriminator] = \
            lambda encoded: self._cop_branch_decoder(encoded, 1)
        self._coprocessor_with_discriminator_decoders[2][Opcodes.bcf[2].discriminator] = \
            lambda encoded: self._cop_branch_decoder(encoded, 2)
        self._coprocessor_with_discriminator_decoders[3][Opcodes.bcf[3].discriminator] = \
            lambda encoded: self._cop_branch_decoder(encoded, 3)
        self._insert_coprocessor_decoders(Opcodes.lwc, Opcodes.swc)

    def decode(self, encoded: EncodedInstruction) -> Instruction:
        return Decoder._decoder(
            self._primary_decoders,
            Opcode.decode_primary(encoded),
            encoded,
            lambda primary: f'Invalid primary opcode 0x{primary:02X}')

    def _insert_primary_opcode_decoders(self, *opcodes: Opcode):
        for opcode in opcodes:
            self._primary_decoders[opcode.primary_opcode] = Decoder._create_from_opcode_decoder(opcode)

    def _insert_secondary_opcode_decoders(self, *opcodes: SecondaryOpcode):
        for opcode in opcodes:
            self._secondary_decoders[opcode.secondary_opcode] = Decoder._create_from_opcode_decoder(opcode)

    def _insert_zero_condition_decoders(self, *opcodes: BranchZeroConditionWithDiscriminatorOpcode):
        for opcode in opcodes:
            self._branch_zero_condition_decoders[opcode.discriminator] = Decoder._create_from_opcode_decoder(opcode)

    def _insert_coprocessor_with_discriminator_decoders(self, *opcodes: tuple[Opcode, ...]):
        for coprocessor_opcodes in opcodes:
            for cop_id, opcode in enumerate(coprocessor_opcodes):
                opcode = typing.cast(_CopNonExecuteCommandOpcodeBase, opcode)
                self._coprocessor_with_discriminator_decoders[cop_id][opcode.discriminator] = \
                    Decoder._create_from_opcode_decoder(opcode)

    def _insert_coprocessor_decoders(self, *opcodes: tuple[Opcode, ...]):
        for coprocessor_opcodes in opcodes:
            self._insert_primary_opcode_decoders(*coprocessor_opcodes)

    def _secondary_opcode_decoder(self, encoded: EncodedInstruction) -> Instruction:
        return Decoder._decoder(
            self._secondary_decoders,
            SecondaryOpcode.decode_secondary(encoded),
            encoded,
            lambda secondary: f'Invalid secondary opcode 0x{secondary:02X}')

    def _branch_zero_condition_with_discriminator_opcode_decoder(self, encoded: EncodedInstruction) -> Instruction:
        return Decoder._decoder(
            self._branch_zero_condition_decoders,
            BranchZeroConditionWithDiscriminatorOpcode.decode_discriminator(encoded),
            encoded,
            lambda discriminator: f'Invalid bXXz discriminator 0x{discriminator:02X}')

    def _cop_non_load_store_decoder(self, encoded: EncodedInstruction, cop_id: int) -> Instruction:
        is_exec_command = _CopNonLoadStoreOpcodeBase.decode_is_exec_command(encoded)
        if is_exec_command:
            return Decoder._instruction_from_opcode(Opcodes.cop[cop_id], encoded)
        else:
            return Decoder._decoder(
                self._coprocessor_with_discriminator_decoders[cop_id],
                _CopNonExecuteCommandOpcodeBase.decode_discriminator(encoded),
                encoded,
                lambda discriminator: '')

    @staticmethod
    def _cop_branch_decoder(encoded: EncodedInstruction, cop_id: int) -> Instruction:
        branch_type = _CopBranchOpcodeBase.decode_branch_type(encoded)
        if branch_type == 0:
            return Decoder._instruction_from_opcode(Opcodes.bcf[cop_id], encoded)
        if branch_type == 1:
            return Decoder._instruction_from_opcode(Opcodes.bct[cop_id], encoded)
        return Decoder._create_invalid_instruction(encoded, f'Invalid cop branch type 0x{branch_type:X}')

    @staticmethod
    def _decoder(
            decoders: list[OpcodeDecoder],
            i: int,
            encoded: EncodedInstruction,
            invalid_cause_creator: Callable[[int], str]) -> Instruction:
        decoder = decoders[i]
        if decoder is not None:
            return decoder(encoded)
        return Decoder._create_invalid_instruction(encoded, invalid_cause_creator(i))

    @staticmethod
    def _create_invalid_instruction(encoded: EncodedInstruction, cause: str):
        return InvalidInstruction(InvalidOpcode(encoded=encoded, cause=cause))

    @staticmethod
    def _create_from_opcode_decoder(opcode: Opcode):
        return lambda encoded: Decoder._instruction_from_opcode(opcode, encoded)

    @staticmethod
    def _instruction_from_opcode(opcode: Opcode, encoded: EncodedInstruction) -> Instruction:
        return Instruction(opcode, opcode.decode_args(encoded))


_decoder = Decoder()


def decode(encoded: EncodedInstruction) -> Instruction:
    return _decoder.decode(encoded)
