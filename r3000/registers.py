import dataclasses


@dataclasses.dataclass
class Register:
    name: str
    alias: str
    index: int | None = None

    def __str__(self) -> str:
        return self.alias

    def has_index(self):
        return self.index is not None

    def instantiate(self) -> 'RuntimeRegister':
        return RuntimeRegister(self)


class RuntimeRegister:
    def __init__(self, register: Register):
        self.register = register
        self._value = 0

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, new_value: int):
        self._value = new_value


cpu_by_index = [
    Register(name=f'R{i}', alias=f'{alias}', index=i)
    for i, alias
    in enumerate([
        'zero',
        'at',
        'v0', 'v1',
        'a0', 'a1', 'a2', 'a3',
        't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
        's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7',
        't8', 't9',
        'k0', 'k1',
        'gp', 'sp', 'fp', 'ra'
    ])]
cpu_by_name = {register.name: register for register in cpu_by_index}
cpu_by_alias = {register.alias: register for register in cpu_by_index}


def _create_cop_by_index(named_registers: dict[int, str], offset: int, unnamed_register_prefix: str):
    named_registers = named_registers or {}
    return [
        Register(
            name=f'R{i + offset}',
            alias=named_registers[i] if i in named_registers else f'{unnamed_register_prefix}R{i}',
            index=i)
        for i
        in range(32)
    ]


def _create_cop_dat_by_index(named_registers: dict[int, str] = None):
    return _create_cop_by_index(named_registers, offset=0, unnamed_register_prefix='dat')


def _create_cop_cnt_by_index(named_registers: dict[int, str] = None):
    return _create_cop_by_index(named_registers, offset=0, unnamed_register_prefix='cnt')


cop_dat_by_index = [
    _create_cop_dat_by_index({
        3: 'BPC', 5: 'BDA', 6: 'TAR', 7: 'DCIC', 8: 'BadA', 9: 'BDAM', 11: 'BPCM', 12: 'SR', 13: 'CAUSE', 14: 'EPC',
        15: 'PRID'
    }),
    _create_cop_dat_by_index(),
    _create_cop_dat_by_index({
        0: 'VXY0', 1: 'VZ0', 2: 'VXY1', 3: 'VZ1', 4: 'VXY2', 5: 'VZ2', 6: 'RGBC', 7: 'OTZ', 8: 'IR0',
        9: 'IR1', 10: 'IR2', 11: 'IR3', 12: 'SXY0', 13: 'SXY1', 14: 'SXY2', 15: 'SXYP',
        16: 'SZ0', 17: 'SZ1', 18: 'SZ2', 19: 'SZ3', 20: 'RGB0', 21: 'RGB1', 22: 'RGB2', 23: 'RES1',
        24: 'MAC0', 25: 'MAC1', 26: 'MAC2', 27: 'MAC3', 28: 'IRGB', 29: 'ORGB', 30: 'LZCS', 31: 'LZCR'
    }),
    _create_cop_dat_by_index()
]
cop_cnt_by_index = [
    _create_cop_cnt_by_index(),
    _create_cop_cnt_by_index(),
    _create_cop_cnt_by_index({
        0: 'RT11_12', 1: 'RT13_21', 2: 'RT22_23', 3: 'RT31_32', 4: 'RT33', 5: 'TRX', 6: 'TRY', 7: 'TRZ',
        8: 'L11_12', 9: 'L13_21', 10: 'L22_23', 11: 'L31_32', 12: 'LL33', 13: 'RBK', 14: 'GBK', 15: 'BBK',
        16: 'LR1_2', 17: 'LR3_G1', 18: 'LG2_3', 19: 'LB1_2', 20: 'LB3', 21: 'RFC', 22: 'GFC', 23: 'BFC',
        24: 'OFX', 25: 'OFY', 26: 'H', 27: 'DQA', 28: 'DQB', 29: 'ZFS3', 30: 'ZFS4', 31: 'FLAG'
    }),
    _create_cop_cnt_by_index()
]
R0 = zero = cpu_by_index[0]
R1 = at = cpu_by_index[1]
R2 = v0 = cpu_by_index[2]
R3 = v1 = cpu_by_index[3]
R4 = a0 = cpu_by_index[4]
R5 = a1 = cpu_by_index[5]
R6 = a2 = cpu_by_index[6]
R7 = a3 = cpu_by_index[7]
R8 = t0 = cpu_by_index[8]
R9 = t1 = cpu_by_index[9]
R10 = t2 = cpu_by_index[10]
R11 = t3 = cpu_by_index[11]
R12 = t4 = cpu_by_index[12]
R13 = t5 = cpu_by_index[13]
R14 = t6 = cpu_by_index[14]
R15 = t7 = cpu_by_index[15]
R16 = s0 = cpu_by_index[16]
R17 = s1 = cpu_by_index[17]
R18 = s2 = cpu_by_index[18]
R19 = s3 = cpu_by_index[19]
R20 = s4 = cpu_by_index[20]
R21 = s5 = cpu_by_index[21]
R22 = s6 = cpu_by_index[22]
R23 = s7 = cpu_by_index[23]
R24 = t8 = cpu_by_index[24]
R25 = t9 = cpu_by_index[25]
R26 = k0 = cpu_by_index[26]
R27 = k1 = cpu_by_index[27]
R28 = gp = cpu_by_index[28]
R29 = sp = cpu_by_index[29]
R30 = fp = cpu_by_index[30]
R31 = ra = cpu_by_index[31]
pc = Register(name='pc', alias='pc')
hi = Register(name='hi', alias='hi')
lo = Register(name='lo', alias='lo')
cop2_datR0 = cop_dat_by_index[2][0]
cop2_datR1 = cop_dat_by_index[2][1]
cop2_datR2 = cop_dat_by_index[2][2]
cop2_datR3 = cop_dat_by_index[2][3]
cop2_datR4 = cop_dat_by_index[2][4]
cop2_datR5 = cop_dat_by_index[2][5]
cop2_datR6 = cop_dat_by_index[2][6]
cop2_datR7 = cop_dat_by_index[2][7]
cop2_datR8 = cop_dat_by_index[2][8]
cop2_datR9 = cop_dat_by_index[2][9]
cop2_datR10 = cop_dat_by_index[2][10]
cop2_datR11 = cop_dat_by_index[2][11]
cop2_datR12 = cop_dat_by_index[2][12]
cop2_datR13 = cop_dat_by_index[2][13]
cop2_datR14 = cop_dat_by_index[2][14]
cop2_datR15 = cop_dat_by_index[2][15]
cop2_datR16 = cop_dat_by_index[2][16]
cop2_datR17 = cop_dat_by_index[2][17]
cop2_datR18 = cop_dat_by_index[2][18]
cop2_datR19 = cop_dat_by_index[2][19]
cop2_datR20 = cop_dat_by_index[2][20]
cop2_datR21 = cop_dat_by_index[2][21]
cop2_datR22 = cop_dat_by_index[2][22]
cop2_datR23 = cop_dat_by_index[2][23]
cop2_datR24 = cop_dat_by_index[2][24]
cop2_datR25 = cop_dat_by_index[2][25]
cop2_datR26 = cop_dat_by_index[2][26]
cop2_datR27 = cop_dat_by_index[2][27]
cop2_datR28 = cop_dat_by_index[2][28]
cop2_datR29 = cop_dat_by_index[2][29]
cop2_datR30 = cop_dat_by_index[2][30]
cop2_datR31 = cop_dat_by_index[2][31]


@dataclasses.dataclass
class ExecutionContext:
    cpu_by_index: list[RuntimeRegister] = dataclasses.field(
        default_factory=lambda: [r.instantiate for r in cpu_by_index])
    cop_dat_by_index: list[list[RuntimeRegister]] = dataclasses.field(
        default_factory=lambda: [[r.instantiate for r in copn_registers] for copn_registers in cop_dat_by_index])
    cop_cnt_by_index: list[list[RuntimeRegister]] = dataclasses.field(
        default_factory=lambda: [[r.instantiate for r in copn_registers] for copn_registers in cop_dat_by_index])
    pc: RuntimeRegister = dataclasses.field(default_factory=pc.instantiate)
    hi: RuntimeRegister = dataclasses.field(default_factory=hi.instantiate)
    lo: RuntimeRegister = dataclasses.field(default_factory=lo.instantiate)
