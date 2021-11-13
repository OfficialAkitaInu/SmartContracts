from pyteal import *
import AkitaInuASAUtils as AIASAU

def ApprovalProgram():
    program = Return(Int(1))
    return compileTeal(program, Mode.Application, version=5)

def ClearProgram():
    program = Return(Int(1))
    return compileTeal(program, Mode.Application, version=5)

def compile(algodClient):
    AIASAU.dumpTealAssembly('assetTimedVault_Approval.teal', ApprovalProgram)
    AIASAU.dumpTealAssembly('assetTimedVault_Clear.teal', ClearProgram)

    AIASAU.compileProgram(algodClient, ApprovalProgram(), 'assetTimedVault_Approval.compiled')
    AIASAU.compileProgram(algodClient, ClearProgram(), 'assetTimedVault_Clear.compiled')

    AIASAU.writeSchema(filePath='localSchema',
                       numInts=0,
                       numBytes=0)
    AIASAU.writeSchema(filePath='globalSchema',
                       numInts=0,
                       numBytes=0)

