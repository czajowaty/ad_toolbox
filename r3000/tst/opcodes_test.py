import unittest
import typing
from r3000 import opcodes, registers
from r3000.opcodes import InvalidInstruction


class OpcodesTest(unittest.TestCase):
    def test_valid_opcodes(self):
        descriptors = [
            (0x00051140, 'sll v0, a1, 0x5', 3),
            (0x000d1302, 'srl v0, t5, 0xC', 3),
            (0x00085403, 'sra t2, t0, 0x10', 3),
            (0x00455004, 'sllv t2, a1, v0', 3),
            (0x00453806, 'srlv a3, a1, v0', 3),
            (0x00622007, 'srav a0, v0, v1', 3),
            (0x03e00008, 'jr ra', 1),
            (0x0040f809, 'jalr v0', 2),
            (0x00408809, 'jalr v0, s1', 2),
            (0x0000000c, 'syscall', 1),
            (0x03ffffcc, 'syscall 0xFFFFF', 1),
            (0x0000000d, 'break', 1),
            (0x0006000d, 'break 0x1800', 1),
            (0x00001810, 'mfhi v1', 1),
            (0x02200011, 'mthi s1', 1),
            (0x00002812, 'mflo a1', 1),
            (0x01200013, 'mtlo t1', 1),
            (0x00510018, 'mult v0, s1', 2),
            (0x00860019, 'multu a0, a2', 2),
            (0x0050001a, 'div v0, s0', 2),
            (0x00a2001b, 'divu a1, v0', 2),
            (0x01428820, 'add s1, t2, v0', 3),
            (0x00628021, 'addu s0, v1, v0', 3),
            (0x016a1022, 'sub v0, t3, t2', 3),
            (0x02501823, 'subu v1, s2, s0', 3),
            (0x02541824, 'and v1, s2, s4', 3),
            (0x00a32025, 'or a0, a1, v1', 3),
            (0x02024826, 'xor t1, s0, v0', 3),
            (0x00051827, 'nor v1, zero, a1', 3),
            (0x0065102a, 'slt v0, v1, a1', 3),
            (0x00c5102b, 'sltu v0, a2, a1', 3),
            (0x04400003, 'bltz v0, 0x800367D8', 2, 0x800367c8),
            (0x0601fffd, 'bgez s0, 0x80037EE0', 2, 0x80037ee8),
            (0x04500003, 'bltzal v0, 0x800367D8', 2, 0x800367c8),
            (0x0611fffd, 'bgezal s0, 0x80037EE0', 2, 0x80037ee8),
            (0x08017ffb, 'j 0x8005FFEC', 1),
            (0x0c01a855, 'jal 0x8006A154', 1),
            (0x10440003, 'beq v0, a0, 0x80010010', 3, 0x80010000),
            (0x1440fff8, 'bne v0, zero, 0x8000FFE4', 3, 0x80010000),
            (0x1840000b, 'blez v0, 0x800637D0', 2, 0x800637a0),
            (0x1c400006, 'bgtz v0, 0x800364B4', 2, 0x80036498),
            (0x23bdffd8, 'addi sp, sp, -0x28', 3),
            (0x24712660, 'addiu s1, v1, 0x2660', 3),
            (0x28e2ff50, 'slti v0, a3, -0xB0', 3),
            (0x2c620008, 'sltiu v0, v1, 0x8', 3),
            (0x30820003, 'andi v0, a0, 0x3', 3),
            (0x36238080, 'ori v1, s1, 0x8080', 3),
            (0x3a640013, 'xori a0, s3, 0x13', 3),
            (0x3c028002, 'lui v0, 0x8002', 2),
            (0x400d1800, 'mfc0 t5, BPC', 2),
            (0x400d2800, 'mfc0 t5, BDA', 2),
            (0x400d3000, 'mfc0 t5, TAR', 2),
            (0x400d3800, 'mfc0 t5, DCIC', 2),
            (0x400d4000, 'mfc0 t5, BadA', 2),
            (0x400d4800, 'mfc0 t5, BDAM', 2),
            (0x400d5800, 'mfc0 t5, BPCM', 2),
            (0x400d6000, 'mfc0 t5, SR', 2),
            (0x400d6800, 'mfc0 t5, CAUSE', 2),
            (0x400d7000, 'mfc0 t5, EPC', 2),
            (0x400d7800, 'mfc0 t5, PRID', 2),
            (0x440d5000, 'mfc1 t5, datR10', 2),
            (0x480d0000, 'mfc2 t5, VXY0', 2),
            (0x480d0800, 'mfc2 t5, VZ0', 2),
            (0x480d1000, 'mfc2 t5, VXY1', 2),
            (0x480d1800, 'mfc2 t5, VZ1', 2),
            (0x480d2000, 'mfc2 t5, VXY2', 2),
            (0x480d2800, 'mfc2 t5, VZ2', 2),
            (0x480d3000, 'mfc2 t5, RGBC', 2),
            (0x480d3800, 'mfc2 t5, OTZ', 2),
            (0x480d4000, 'mfc2 t5, IR0', 2),
            (0x480d4800, 'mfc2 t5, IR1', 2),
            (0x480d5000, 'mfc2 t5, IR2', 2),
            (0x480d5800, 'mfc2 t5, IR3', 2),
            (0x480d6000, 'mfc2 t5, SXY0', 2),
            (0x480d6800, 'mfc2 t5, SXY1', 2),
            (0x480d7000, 'mfc2 t5, SXY2', 2),
            (0x480d7800, 'mfc2 t5, SXYP', 2),
            (0x480d8000, 'mfc2 t5, SZ0', 2),
            (0x480d8800, 'mfc2 t5, SZ1', 2),
            (0x480d9000, 'mfc2 t5, SZ2', 2),
            (0x480d9800, 'mfc2 t5, SZ3', 2),
            (0x480da000, 'mfc2 t5, RGB0', 2),
            (0x480da800, 'mfc2 t5, RGB1', 2),
            (0x480db000, 'mfc2 t5, RGB2', 2),
            (0x480db800, 'mfc2 t5, RES1', 2),
            (0x480dc000, 'mfc2 t5, MAC0', 2),
            (0x480dc800, 'mfc2 t5, MAC1', 2),
            (0x480dd000, 'mfc2 t5, MAC2', 2),
            (0x480dd800, 'mfc2 t5, MAC3', 2),
            (0x480de000, 'mfc2 t5, IRGB', 2),
            (0x480de800, 'mfc2 t5, ORGB', 2),
            (0x480df000, 'mfc2 t5, LZCS', 2),
            (0x480df800, 'mfc2 t5, LZCR', 2),
            (0x4c0d5000, 'mfc3 t5, datR10', 2),
            (0x404c2000, 'cfc0 t4, cntR4', 2),
            (0x444c2000, 'cfc1 t4, cntR4', 2),
            (0x484c0000, 'cfc2 t4, RT11_12', 2),
            (0x484c0800, 'cfc2 t4, RT13_21', 2),
            (0x484c1000, 'cfc2 t4, RT22_23', 2),
            (0x484c1800, 'cfc2 t4, RT31_32', 2),
            (0x484c2000, 'cfc2 t4, RT33', 2),
            (0x484c2800, 'cfc2 t4, TRX', 2),
            (0x484c3000, 'cfc2 t4, TRY', 2),
            (0x484c3800, 'cfc2 t4, TRZ', 2),
            (0x484c4000, 'cfc2 t4, L11_12', 2),
            (0x484c4800, 'cfc2 t4, L13_21', 2),
            (0x484c5000, 'cfc2 t4, L22_23', 2),
            (0x484c5800, 'cfc2 t4, L31_32', 2),
            (0x484c6000, 'cfc2 t4, LL33', 2),
            (0x484c6800, 'cfc2 t4, RBK', 2),
            (0x484c7000, 'cfc2 t4, GBK', 2),
            (0x484c7800, 'cfc2 t4, BBK', 2),
            (0x484c8000, 'cfc2 t4, LR1_2', 2),
            (0x484c8800, 'cfc2 t4, LR3_G1', 2),
            (0x484c9000, 'cfc2 t4, LG2_3', 2),
            (0x484c9800, 'cfc2 t4, LB1_2', 2),
            (0x484ca000, 'cfc2 t4, LB3', 2),
            (0x484ca800, 'cfc2 t4, RFC', 2),
            (0x484cb000, 'cfc2 t4, GFC', 2),
            (0x484cb800, 'cfc2 t4, BFC', 2),
            (0x484cc000, 'cfc2 t4, OFX', 2),
            (0x484cc800, 'cfc2 t4, OFY', 2),
            (0x484cd000, 'cfc2 t4, H', 2),
            (0x484cd800, 'cfc2 t4, DQA', 2),
            (0x484ce000, 'cfc2 t4, DQB', 2),
            (0x484ce800, 'cfc2 t4, ZFS3', 2),
            (0x484cf000, 'cfc2 t4, ZFS4', 2),
            (0x484cf800, 'cfc2 t4, FLAG', 2),
            (0x4c4c2000, 'cfc3 t4, cntR4', 2),
            (0x40846000, 'mtc0 a0, SR', 2),
            (0x44846000, 'mtc1 a0, datR12', 2),
            (0x48846000, 'mtc2 a0, SXY0', 2),
            (0x4c846000, 'mtc3 a0, datR12', 2),
            (0x40ca5800, 'ctc0 t2, cntR11', 2),
            (0x44ca5800, 'ctc1 t2, cntR11', 2),
            (0x48ca5800, 'ctc2 t2, L31_32', 2),
            (0x4cca5800, 'ctc3 t2, cntR11', 2),
            (0x41001000, 'bc0f 0x80024004', 1, 0x80020000),
            (0x4500f000, 'bc1f 0x8001C004', 1, 0x80020000),
            (0x49002000, 'bc2f 0x80028004', 1, 0x80020000),
            (0x4d00e000, 'bc3f 0x80018004', 1, 0x80020000),
            (0x41011000, 'bc0t 0x80024004', 1, 0x80020000),
            (0x4501f000, 'bc1t 0x8001C004', 1, 0x80020000),
            (0x49012000, 'bc2t 0x80028004', 1, 0x80020000),
            (0x4d01e000, 'bc3t 0x80018004', 1, 0x80020000),
            (0x4318042f, 'cop0 0x118042F', 1),
            (0x4718042f, 'cop1 0x118042F', 1),
            (0x4b18042f, 'cop2 0x118042F', 1),
            (0x4f18042f, 'cop3 0x118042F', 1),
            (0xc1a50010, 'lwc0 BDA, 0x10(t5)', 3),
            (0xc5a50500, 'lwc1 datR5, 0x500(t5)', 3),
            (0xc9a5ff00, 'lwc2 VZ2, -0x100(t5)', 3),
            (0xcda5ffd0, 'lwc3 datR5, -0x30(t5)', 3),
            (0xe1a50010, 'swc0 BDA, 0x10(t5)', 3),
            (0xe5a50500, 'swc1 datR5, 0x500(t5)', 3),
            (0xe9a5ff00, 'swc2 VZ2, -0x100(t5)', 3),
            (0xeda5ffd0, 'swc3 datR5, -0x30(t5)', 3),
            (0x82420071, 'lb v0, 0x71(s2)', 3),
            (0x8663ff80, 'lh v1, -0x80(s3)', 3),
            (0x88e30003, 'lwl v1, 0x3(a3)', 3),
            (0x8fb60028, 'lw s6, 0x28(sp)', 3),
            (0x9043d196, 'lbu v1, -0x2E6A(v0)', 3),
            (0x94830008, 'lhu v1, 0x8(a0)', 3),
            (0x98e2ffff, 'lwr v0, -0x1(a3)', 3),
            (0xa1260016, 'sb a2, 0x16(t1)', 3),
            (0xa602ffa0, 'sh v0, -0x60(s0)', 3),
            (0xaa020003, 'swl v0, 0x3(s0)', 3),
            (0xafbf0010, 'sw ra, 0x10(sp)', 3),
            (0xb8c2fffe, 'swr v0, -0x2(a2)', 3)
        ]
        context = registers.ExecutionContext()
        context.pc.value = 0x80010000
        for i, instruction_descriptor in enumerate(descriptors):
            encoded = instruction_descriptor[0]
            expected_instruction_string = instruction_descriptor[1]
            expected_args_number = instruction_descriptor[2]
            if len(instruction_descriptor) > 3:
                context.pc.value = instruction_descriptor[3]
            instruction = opcodes.decode(encoded)
            instruction_string = instruction.to_string(context)
            if instruction_string != expected_instruction_string:
                self.fail(
                    f"Instruction #{i}. Encoded: 0x{encoded:08x}. "
                    f"Decoded: {instruction.opcode.name} {instruction.args}. "
                    f"Mnemonic: '{instruction_string}' vs expected '{expected_instruction_string}'")
            if instruction.opcode.args_number != expected_args_number:
                self.fail(
                    f"Instruction #{i}. Encoded: 0x{encoded:08x}. "
                    f"Decoded: {instruction.opcode.name} {instruction.args}. "
                    f"Args number: {instruction.opcode.args_number} vs expected {expected_args_number}")
            encoded_back = instruction.encode()
            if encoded != encoded_back:
                self.fail(
                    f"Instruction #{i}. Encoded {encoded:08x}. "
                    f"Decoded: {instruction.opcode.name} {instruction.args}. "
                    f"Encoded back {encoded_back:08x} differs.")

    def test_invalid_opcodes(self):
        descriptors = [
            (0x50123456, 'Invalid primary opcode 0x14'),
            (0xffffffff, 'Invalid primary opcode 0x3F'),
            (0x00876501, 'Invalid secondary opcode 0x01'),
            (0x0408468a, 'Invalid bXXz discriminator 0x08'),
            (0x41100000, 'Invalid cop branch type 0x10')
        ]
        context = registers.ExecutionContext()
        for i, descriptor in enumerate(descriptors):
            encoded, expected_cause = descriptor
            instruction = opcodes.decode(encoded)
            instruction_string = instruction.to_string(context)
            if instruction.is_valid() or instruction_string != 'invalid':
                self.fail(f"Instruction #{i}. Encoded: 0x{encoded:08x}. Valid instruction: {instruction_string}.")
            instruction = typing.cast(InvalidInstruction, instruction)
            if instruction.opcode.cause != expected_cause:
                self.fail(
                    f"Instruction #{i}. Encoded: 0x{encoded:08x}. "
                    f"Cause '{instruction.opcode.cause}' vs expected '{expected_cause}'.")
            encoded_back = instruction.encode()
            if encoded != encoded_back:
                self.fail(f"Instruction #{i}. Encoded {encoded:08x}. Encoded back {encoded_back:08x} differs.")


if __name__ == '__main__':
    unittest.main()
