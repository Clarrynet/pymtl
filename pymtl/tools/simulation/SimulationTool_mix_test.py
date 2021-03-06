#=======================================================================
# SimulationTool_mix_test.py
#=======================================================================
# Mixed (combinational and sequential) logic tests for SimulationTool.

import pytest

from pymtl import *

from SimulationTool_comb_test import (
  PassThrough, verify_bit_blast,
  ComplexBitBlast as CombBitBlast,
)

from SimulationTool_struct_test import (
  ComplexBitBlastStruct as StructBitBlast,
)

from SimulationTool_seq_test import (
  Register, register_tester,
  setup_sim, local_setup_sim,
)

#-----------------------------------------------------------------------
# register_tester
#-----------------------------------------------------------------------
def register_tester( model_type, setup_sim ):
  model      = model_type( 16 )
  model, sim = setup_sim( model )
  model.in_.v = 8
  assert model.out == 0
  sim.cycle()
  assert model.out == 8
  model.in_.v = 9
  assert model.out == 8
  model.in_.v = 10
  sim.cycle()
  assert model.out == 10
  model.in_.v = 2
  sim.cycle()
  assert model.out == 2

#-----------------------------------------------------------------------
# RegisterPassThrough
#-----------------------------------------------------------------------

class RegisterPassThrough( Model ):
  def __init__( s, nbits ):
    s.nbits  = nbits
    s.in_    = InPort  ( nbits )
    s.out    = OutPort ( nbits )

  def elaborate_logic( s ):
    s.reg0 = Register    ( s.nbits )
    s.pt   = PassThrough ( s.nbits )

    s.connect( s.in_,      s.reg0.in_ )
    s.connect( s.reg0.out, s.pt.in_   )
    s.connect( s.pt.out,   s.out      )

def test_RegisterPassThrough( setup_sim ):
  register_tester( RegisterPassThrough, setup_sim )

#-----------------------------------------------------------------------
# PassThroughRegister
#-----------------------------------------------------------------------

class PassThroughRegister( Model ):
  def __init__( s, nbits ):
    s.nbits  = nbits
    s.in_    = InPort  ( nbits )
    s.out    = OutPort ( nbits )

  def elaborate_logic( s ):
    s.pt   = PassThrough ( s.nbits )
    s.reg0 = Register    ( s.nbits )

    s.connect( s.in_,      s.pt.in_   )
    s.connect( s.pt.out,   s.reg0.in_ )
    s.connect( s.reg0.out, s.out      )

def test_PassThroughRegister( setup_sim ):
  register_tester( PassThroughRegister, setup_sim )

#-----------------------------------------------------------------------
# splitslice_tester
#-----------------------------------------------------------------------
# Test registered slicing followed by combinational logic

def splitslice_tester( model_type, setup_sim ):
  model      = model_type()
  model, sim = setup_sim( model )
  sim.cycle()
  model.in_.v = 0b1001
  assert model.out0 == 0b00
  assert model.out1 == 0b00
  sim.cycle()
  assert model.out0 == 0b01
  assert model.out1 == 0b10
  model.in_.v = 0b1111
  sim.cycle()
  assert model.out0 == 0b11
  assert model.out1 == 0b11

#-----------------------------------------------------------------------
# RegSlicePassThrough
#-----------------------------------------------------------------------

class RegSlicePassThrough( Model ):
  def __init__( s ):
    s.in_  = InPort  ( 4 )
    s.out0 = OutPort ( 2 )
    s.out1 = OutPort ( 2 )

  def elaborate_logic( s ):
    s.pass0  = PassThrough( 2 )
    s.pass1  = PassThrough( 2 )

    @s.posedge_clk
    def seq_logic():
      s.pass0.in_.n = s.in_[0:2]
      s.pass1.in_.n = s.in_[2:4]

    s.connect( s.pass0.out, s.out0 )
    s.connect( s.pass1.out, s.out1 )

def test_RegSlicePassThrough( setup_sim ):
  splitslice_tester( RegSlicePassThrough, setup_sim )

#-----------------------------------------------------------------------
# RegSlicePassThroughWire
#-----------------------------------------------------------------------

class RegSlicePassThroughWire( Model ):
  def __init__( s ):
    s.in_  = InPort  ( 4 )
    s.out0 = OutPort ( 2 )
    s.out1 = OutPort ( 2 )

  def elaborate_logic( s ):
    s.wire0 = Wire( 2 )
    s.wire1 = Wire( 2 )

    @s.posedge_clk
    def seq_logic():
      s.wire0.n    = s.in_[0:2]
      # This doesn't work, should it?
      #s.wire1[:].n = s.in_[2:4]
      s.wire1.n    = s.in_[2:4]

    @s.combinational
    def wire0_logic():
      s.out0.v = s.wire0

    @s.combinational
    def wire1_logic():
      s.out1.v = s.wire1

def test_RegSlicePassThroughWire( setup_sim ):
  splitslice_tester( RegSlicePassThroughWire, setup_sim )

#-----------------------------------------------------------------------
# RegisterBitBlast
#-----------------------------------------------------------------------

class RegisterBitBlast( Model ):
  def __init__( s, nbits, subclass ):
    s.nbits     = nbits
    s.subclass  = subclass
    s.groupings = 2
    s.in_ = InPort( nbits )
    s.out = [ OutPort( s.groupings ) for x in
              xrange( 0, nbits, s.groupings ) ]

  def elaborate_logic( s ):
    # Submodules
    s.reg0  = Register( s.nbits )
    s.split = s.subclass( s.nbits, s.groupings )
    # Connections
    s.connect( s.in_     , s.reg0.in_  )
    s.connect( s.reg0.out, s.split.in_ )
    for i, x in enumerate( s.out ):
      s.connect( s.split.out[i], x )

def register_bit_blast_tester( model, setup_sim ):
  model, sim = setup_sim( model )
  transl     = not hasattr( model, 'reg0' )
  sim.reset()
  model.in_.v = 0b11110000
  verify_bit_blast( model.out, 0b0 )
  if not transl: assert model.reg0.out.v  == 0b0
  sim.cycle()
  if not transl: assert model.reg0.out.v  == 0b11110000
  if not transl: assert model.split.in_.v == 0b11110000
  if not transl: verify_bit_blast( model.split.out, 0b11110000 )
  verify_bit_blast( model.out,       0b11110000 )
  model.in_.v = 0b1111000011001010
  if not transl: assert model.reg0.out.v  == 0b11110000
  if not transl: assert model.split.in_.v == 0b11110000
  if not transl: verify_bit_blast( model.split.out, 0b11110000 )
  verify_bit_blast( model.out,       0b11110000 )
  sim.cycle()
  if not transl: assert model.reg0.out.v  == 0b1111000011001010
  verify_bit_blast( model.out, 0b1111000011001010 )

# FIXME: Caching does not work properly on the RegisterBitBlast module.
# This is because a Model is passed in as a parameter, the hash function
# used to generated identifier for the cache is problem using the model
# object id(), which changes from run to run.

def test_RegisterCombBitBlast( setup_sim ):
  model = RegisterBitBlast( 16, CombBitBlast )
  register_bit_blast_tester( model, setup_sim )

def test_RegisterStructBitBlast( setup_sim ):
  model = RegisterBitBlast( 16, StructBitBlast )
  register_bit_blast_tester( model, setup_sim )

#-----------------------------------------------------------------------
# WriteThenReadCombSubmod
#-----------------------------------------------------------------------
# TODO: THIS MODEL CURRENTLY CAUSES AN INFINITE LOOP IN PYTHON DUE TO THE
#       WAY WE DETECT SENSITIVITY LISTS... if a combinational submodule
#       is written, its @s.combinational block get's added to the event
#       queue.  After the submodule's concurrent block fires, it adds
#       the parent's concurrent block on the queue again, this continues
#       forever. Fix.
#
# UPDATE: FIXED!

class WriteThenReadCombSubmod( Model ):
  def __init__( s, nbits ):
    s.nbits   = nbits
    s.in_     = InPort ( nbits )
    s.out     = OutPort( nbits )

  def elaborate_logic( s ):

    s.submod = PassThrough( s.nbits )

    @s.combinational
    def comb_logic():
      s.submod.in_.v = s.in_
      s.out.v        = s.submod.out

def test_WriteThenReadCombSubmod( setup_sim ):
  model      = WriteThenReadCombSubmod( 16 )
  model, sim = setup_sim( model )
  for i in range( 10 ):
    model.in_.v = i
    #assert False   # Prevent infinite loop!
    sim.cycle()
    assert model.out == i

#-----------------------------------------------------------------------
# SliceWriteCheck
#-----------------------------------------------------------------------
# Test updates to slices.
class SliceWriteCheck( Model ):

  def __init__( s, nbits ):
    assert nbits == 16
    s.in_ = InPort  ( 16 )
    s.out = OutPort ( 16 )

  def elaborate_logic( s ):
    s.m0 = PassThrough( 16 )
    s.connect( s.in_, s.m0.in_ )
    s.connect( s.out, s.m0.out )

def test_SliceWriteCheck( setup_sim ):

  model = SliceWriteCheck( 16 )
  model, sim = setup_sim( model )
  assert model.out == 0

  # Test regular write
  model.in_.n = 8
  sim.cycle()
  assert model.out == 0b1000

  # Slice then .n, should pass
  model.in_[0].n = 1
  sim.cycle()
  assert model.out == 0b1001
  model.in_[4:8].n = 0b1001
  sim.cycle()
  assert model.out == 0b10011001

  # Test regular write
  model.in_.n = 8
  sim.cycle()
  assert model.out == 0b1000

  # Only slice, should fail
  model.in_[0] = 1
  sim.cycle()
  with pytest.raises( AssertionError ):
    assert model.out == 0b1001
  model.in_[4:8] = 0b1001
  sim.cycle()
  with pytest.raises( AssertionError ):
    assert model.out == 0b10011001

  # Test regular write
  model.in_.n = 8
  sim.cycle()
  assert model.out == 0b1000

  # .n then slice, should fail
  model.in_.n[0] = 1
  sim.cycle()
  with pytest.raises( AssertionError ):
    assert model.out == 0b1001
  model.in_.n[4:8] = 0b1001
  sim.cycle()
  with pytest.raises( AssertionError ):
    assert model.out == 0b10011001

#-----------------------------------------------------------------------
# OutputToRegInput
#-----------------------------------------------------------------------
# Test updates to slices.
class OutputToRegInput( Model ):
  def __init__( s, nbits ):
    s.nbits  = nbits
    s.in_    = InPort  ( nbits )
    s.out    = OutPort ( nbits )
    s.other  = OutPort ( nbits )
  def elaborate_logic( s ):
    s.reg_ = Register( s.nbits )
    s.connect( s.in_, s.other )
    s.connect( s.reg_.in_, s.other )
    s.connect( s.reg_.out, s.out   )

def test_OutputToRegInput( setup_sim ):
  register_tester( OutputToRegInput, setup_sim )

#-----------------------------------------------------------------------
# OutputToRegInputSlice
#-----------------------------------------------------------------------
class OutputToRegInputSlice( Model ):
  def __init__( s, nbits ):
    s.nbits  = nbits
    s.in_    = InPort  ( nbits )
    s.out    = OutPort ( nbits )
    s.other  = OutPort ( nbits )
  def elaborate_logic( s ):
    s.reg_ = Register( s.nbits )
    s.connect( s.in_, s.other )
    for i in range( s.nbits ):
      s.connect( s.reg_.in_[i], s.other[i] )
    s.connect( s.reg_.out, s.out   )

def test_OutputToRegInputSlice( setup_sim ):
  register_tester( OutputToRegInputSlice, setup_sim )

#-----------------------------------------------------------------------
# OutputToRegInput_Comb
#-----------------------------------------------------------------------
# Test updates to slices.
class OutputToRegInput_Comb( Model ):
  def __init__( s, nbits ):
    s.nbits  = nbits
    s.in_    = InPort  ( nbits )
    s.out    = OutPort ( nbits )
    s.other  = OutPort ( nbits )
  def elaborate_logic( s ):
    s.reg_ = Register( s.nbits )

    @s.combinational
    def comb():
      s.other.value = s.in_

    s.connect( s.reg_.in_, s.other )
    s.connect( s.reg_.out, s.out   )

def test_OutputToRegInput_Comb( setup_sim ):
  register_tester( OutputToRegInput_Comb, setup_sim )

#-----------------------------------------------------------------------
# OutputToRegInputSlice_Comb
#-----------------------------------------------------------------------
class OutputToRegInputSlice_Comb( Model ):
  def __init__( s, nbits ):
    s.nbits  = nbits
    s.in_    = InPort  ( nbits )
    s.out    = OutPort ( nbits )
    s.other  = OutPort ( nbits )
  def elaborate_logic( s ):
    s.reg_ = Register( s.nbits )

    @s.combinational
    def comb():
      s.other.value = s.in_

    for i in range( s.nbits ):
      s.connect( s.reg_.in_[i], s.other[i] )
    s.connect( s.reg_.out, s.out   )

def test_OutputToRegInputSlice_Comb( setup_sim ):
  register_tester( OutputToRegInputSlice_Comb, setup_sim )
