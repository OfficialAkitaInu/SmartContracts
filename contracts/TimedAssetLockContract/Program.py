from akita_inu_asa_utils import *
from pyteal import *

def approval_program():
    program = Return(Int(1))
    return compileTeal(program, Mode.Application, version=5)


def clear_program():
    program = Return(Int(1))
    return compileTeal(program, Mode.Application, version=5)


def compile(algodClient):
    dump_teal_assembly('assetTimedVault_Approval.teal', approval_program)
    dump_teal_assembly('assetTimedVault_Clear.teal', clear_program)

    compile_program(algodClient, approval_program(), 'assetTimedVault_Approval.compiled')
    compile_program(algodClient, clear_program(), 'assetTimedVault_Clear.compiled')

    write_schema(file_path='localSchema',
                 num_ints=0,
                 num_bytes=0)
    write_schema(file_path='globalSchema',
                 num_ints=0,
                 num_bytes=0)

