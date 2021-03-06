#@C Copyright Notice
#@C ================
#@C This file is part of cpswTreeGUI. It is subject to the license terms in the
#@C LICENSE.txt file found in the top-level directory of this distribution and at
#@C
#@C https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
#@C
#@C No part of cpswTreeGUI, including this file, may be copied, modified, propagated, or
#@C distributed except according to the terms contained in the LICENSE.txt file.
import yaml_cpp as yaml
import cpswTreeGUI
from   cpswAdaptBase     import *
from   hashlib           import sha1
import epics

class CAAdaptBase:
  def __init__(self, path, suff, needCtrl=False):
    self._path = path
    self._hnam = path.hash(suff)
    self._suff = suff;
    if needCtrl:
      form       = 'ctrl'
    else:
      form       = 'native'
    self._pv   = epics.get_pv(self._hnam, form=form, connection_timeout=0.0)

  def hnam(self):
    return self._hnam

  def path(self):
    return self._path

  def pv(self):
    return self._pv

  def getConnectionName(self):
    return self.path().getFull(self._suff)

class CmdAdapt(AdaptBase, CAAdaptBase):
  def __init__(self, cmd):
    AdaptBase.__init__(self, cmd)
    CAAdaptBase.__init__(self, PathAdapt( cmd.getPath() ), "Ex")

  def execute(self):
    self._pv.put("Run")

  def getConnectionName(self):
    return CAAdaptBase.getConnectionName( self )

class StreamAdapt(AdaptBase, CAAdaptBase):
  def __init__(self, strm):
    #AdaptBase.__init__(self, strm)
    raise NotImplemented("STREAM not implemented for CA")

  def getConnectionName(self):
    return CAAdaptBase.getConnectionName( self )

class VarAdapt(VarAdaptBase, CAAdaptBase):

  def __init__(self, svb, readOnly, reprType):
    VarAdaptBase.__init__(self, svb, readOnly, reprType)
    CAAdaptBase.__init__(self, PathAdapt( svb.getPath() ), "Rd", self.hasEnums())

    self.signoff_ = 0
    if not svb.isSigned() and not self.hasEnums():
      self.signoff_ = 1 << svb.getSizeBits()


    if not readOnly:
      self._pvw     = epics.get_pv(self.path().hash("St"), connection_timeout=0.0)
    print("Made PV: '{}' -- type '{}'".format(self.hnam(), self.pv().type))

  def setVal(self, val, fromIdx = -1, toIdx = -1):
    self._pvw.put( val )

  def setWidget(self, widgt):
    VarAdaptBase.setWidget(self, widgt)
    self.pv().add_callback(self, with_ctrlvars=False)
    asStr = self.hasEnums()
    val = self.pv().get( timeout=0.0, as_string=asStr )
    if None != val:
      if asStr:
        val = str(val, "ascii")
      # if connection was fast we must update
      self.callback( val )

  def getValAsync(self):
    raise NotImplemented("getValAsync not implemented for CA")

  # Called by Async IO Completion
  def callback(self, value):
    self._widgt.asyncUpdateWidget( value )

  def __call__(self, **kwargs):
    if self.hasEnums():
      val = str(kwargs["char_value"], "ASCII")
    else:
      val = kwargs["value"]
      if not self.isString() and val < 0:
        val = val + self.signoff_
    self.callback( val )

  def getConnectionName(self):
    return CAAdaptBase.getConnectionName( self )

class ChildAdapt(ChildAdaptBase):

  @staticmethod
  def mkChildAdapt(chld):
    return ChildAdapt(chld)

  def __init__(self, chld):
    ChildAdaptBase.__init__(self, chld)

  def findByName(self, el):
    return PathAdapt( ChildAdaptBase.findByName( self, el ) )

class PathAdapt(PathAdaptBase):

  @staticmethod
  def loadYamlFile(yamlFile, yamlRoot, yamlIncDir = None, fixYaml = None):
    return PathAdapt( PathAdaptBase.loadYamlFile( yamlFile, yamlRoot, yamlIncDir, fixYaml ) )

  def __init__(self, p):
    PathAdaptBase.__init__(self, p)

  def guessRepr(self):
    rval = PathAdaptBase.guessRepr(self)
    if None == rval:
      rval = cpswTreeGUI._ReprInt
    return rval

  def findByName(self, el):
    return PathAdapt( self.getp().findByName( el ) )

  def loadConfigFromYamlFile(self, yaml_file):
    raise NotImplemented("loadConfigFromYamlFile not implemented")

  def createVar(self):
    scalVal, ro, representation = PathAdaptBase.createVar( self )
    return VarAdapt( scalVal, ro, representation )

  def createCmd(self):
    cmd = PathAdaptBase.createCmd( self )
    return CmdAdapt( cmd )

  def createStream(self):
    raise cpswTreeGUI.InterfaceNotImplemented("Streams not implemented")

  def getFull(self, suff=""):
   	return cpswTreeGUI._HashPrefix + self.toString() + suff

  def hash(self, suff):
    namLim     = cpswTreeGUI._HashedNameLenMax
    recPrefix  = cpswTreeGUI._RecordNamePrefix
    hnam = recPrefix + sha1( bytearray( self.getFull(suff) , "ascii" ) ).hexdigest().upper()
    hnam = hnam[0:namLim]
    return hnam
