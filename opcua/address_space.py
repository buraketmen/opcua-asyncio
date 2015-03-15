
import logging

from opcua import ua

class AttributeValue(object):
    def __init__(self, value):
        self.value = value
        self.value_callback = None 
        self.data_change_callback = None 

    def __str__(self):
        return "AttributeValue({})".format(self.value)
    __repr__ = __str__

class NodeData(object):
    def __init__(self, nodeid):
        self.nodeid = nodeid
        self.attributes = {}
        self.references = []

    def __str__(self):
        return "NodeData(id:{}, attrs:{}, refs:{})".format(self.nodeid, self.attributes, self.references)
    __repr__ = __str__

class AddressSpace(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._nodes = {}


    def add_nodes(self, addnodeitems):
        results = []
        for item in addnodeitems:
            results.append(self._add_node(item))
        return results

    def _add_node(self, item):
        result = ua.AddNodesResult()

        if item.RequestedNewNodeId in self._nodes:
            self.logger.warn("AddNodeItem: node already exists")
            result.StatusCode = ua.StatusCode(ua.StatusCodes.BadNodeIdExists)
            return result
        nodedata = NodeData(item.RequestedNewNodeId)
        #add common attrs
        nodedata.attributes[ua.AttributeIds.BrowseName] = AttributeValue(ua.DataValue(ua.Variant(item.BrowseName, ua.VariantType.QualifiedName)))
        nodedata.attributes[ua.AttributeIds.NodeClass] = AttributeValue(ua.DataValue(ua.Variant(item.NodeClass, ua.VariantType.Int32)))
        #add requested attrs
        self._add_nodeattributes(item.Attributes, nodedata)

        self._nodes[item.RequestedNewNodeId] = nodedata

        if item.ParentNodeId == ua.NodeId():
            self.logger.warn("add_node: creating node %s without parent", item.RequestedNewNodeId) 
        elif not item.ParentNodeId in self._nodes:
            self.logger.warn("add_node: while adding node %s, requested parent node %s does not exists", item.RequestedNewNodeId, item.ParentNodeId) 
        else:
            desc = ua.ReferenceDescription()
            desc.ReferenceTypeId = item.ReferenceTypeId
            desc.NodeId = item.RequestedNewNodeId
            desc.NodeClass = item.NodeClass
            desc.BrowseName = item.BrowseName
            desc.DisplayName = ua.LocalizedText(item.BrowseName.Name)
            desc.TargetNodeTypeDefinition = item.TypeDefinition
            desc.IsForward = True

            self._nodes[item.ParentNodeId].references.append(desc)
        
        if item.TypeDefinition != ua.NodeId():
            #type definition
            addref = ua.AddReferencesItem()
            addref.SourceNodeId = item.RequestedNewNodeId
            addref.IsForward = True
            addref.ReferenceTypeId = ua.ObjectIds.HasTypeDefinition
            addref.TargetNodeId = item.TypeDefinition
            addref.NodeClass = ua.NodeClass.DataType
            self._add_reference(addref)

        result.StatusCode = ua.StatusCode()
        result.AddedNodeId = item.RequestedNewNodeId

        return result

    def add_references(self, refs):
        result = []
        for ref in refs:
            result.append(self._add_reference(ref))
        return result

    def _add_reference(self, addref):
        if not addref.SourceNodeId in self._nodes:
            self.logger.warn("add_reference: source node %s does not exists", addref.SourceNodeId)
            return ua.StatusCode(ua.StatusCodes.BadSourceNodeIdInvalid)
        # we accept reference to whatever nodes, this seems to be necessary in many cases, where target node may be added later
        #if not addref.TargetNodeId in self._nodes:
            #self.logger.warn("add_reference: target node %s does not exists", addref.TargetNodeId)
            #return ua.StatusCode(ua.StatusCodes.BadTargetNodeIdInvalid)
        rdesc = ua.ReferenceDescription()
        rdesc.ReferencetypeId = addref.ReferenceTypeId
        rdesc.IsForware = addref.IsForward
        rdesc.NodeId = addref.TargetNodeId
        rdesc.NodeClass = addref.NodeClass
        rdesc.BrowseName = self.get_attribute_value(addref.TargetNodeId, ua.AttributeIds.BrowseName)
        rdesc.DisplayName = self.get_attribute_value(addref.TargetNodeId, ua.AttributeIds.DisplayName)
        self._nodes[addref.SourceNodeId].references.append(rdesc)
        return ua.StatusCode()

    def get_attribute_value(self, nodeid, attr):
        #self.logger.debug("get attr val: %s %s", nodeid, attr)
        dv = ua.DataValue()
        if not nodeid in self._nodes:
            dv.StatusCode = ua.StatusCode(ua.StatusCodes.BadNodeIdUnknown)
            return dv
        node = self._nodes[nodeid]
        if not attr in node.attributes:
            dv.StatusCode = ua.StatusCode(ua.StatusCodes.BadAttributeIdInvalid)
            return dv
        attval = node.attributes[attr]
        if attval.value_callback:
            return attval.value_callback()
        return attval.value

    def set_attribute_value(self, nodeid, attr, value):
        self.logger.debug("set attr val: %s %s %s", nodeid, attr, value)
        if not nodeid in self._nodes:
            return ua.StatusCode(ua.StatusCodes.BadNodeIdUnknown)
        node = self._nodes[nodeid]
        if not attr in node.attributes:
            return ua.StatusCode(ua.StatusCodes.BadAttributeIdInvalid)
        attval = node.attributes[attr]
        attval.value = value
        if attval.datachange_callback:
            return attval.value_callback(nodeid, attr, value)
        return ua.StatusCode()

    def _add_nodeattributes(self, item, nodedata):
        item = ua.downcast_extobject(item)
        if item.SpecifiedAttributes & ua.NodeAttributesMask.AccessLevel:
            nodedata.attributes[ua.AttributeIds.AccessLevel] = AttributeValue(ua.DataValue(ua.Variant(item.AccessLevel, ua.VariantType.Byte)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.ArrayDimensions:
            nodedata.attributes[ua.AttributeIds.ArrayDimensions] = AttributeValue(ua.DataValue(ua.Variant(item.ArrayDimensions, ua.VariantType.Int32)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.BrowseName:
            nodedata.attributes[ua.AttributeIds.BrowseName] = AttributeValue(ua.DataValue(ua.Variant(item.BrowseName, ua.VariantType.QualifiedName)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.ContainsNoLoops:
            nodedata.attributes[ua.AttributeIds.ContainsNoLoops] = AttributeValue(ua.DataValue(ua.Variant(item.ContainsNoLoops, ua.VariantType.Boolean)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.DataType:
            nodedata.attributes[ua.AttributeIds.DataType] = AttributeValue(ua.DataValue(ua.Variant(item.DataType, ua.VariantType.NodeId)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.DataType:
            nodedata.attributes[ua.AttributeIds.Description] = AttributeValue(ua.DataValue(ua.Variant(item.Description, ua.VariantType.LocalizedText)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.DisplayName:
            nodedata.attributes[ua.AttributeIds.DisplayName] = AttributeValue(ua.DataValue(ua.Variant(item.DisplayName, ua.VariantType.LocalizedText)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.EventNotifier:
            nodedata.attributes[ua.AttributeIds.EventNotifier] = AttributeValue(ua.DataValue(ua.Variant(item.EventNotifier, ua.VariantType.Boolean)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.Executable:
            nodedata.attributes[ua.AttributeIds.Executable] = AttributeValue(ua.DataValue(ua.Variant(item.Executable, ua.VariantType.Boolean)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.Historizing:
            nodedata.attributes[ua.AttributeIds.Historizing] = AttributeValue(ua.DataValue(ua.Variant(item.Historizing, ua.VariantType.Boolean)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.InverseName:
            nodedata.attributes[ua.AttributeIds.InverseName] = AttributeValue(ua.DataValue(ua.Variant(item.InverseName, ua.VariantType.LocalizedText)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.IsAbstract:
            nodedata.attributes[ua.AttributeIds.IsAbstract] = AttributeValue(ua.DataValue(ua.Variant(item.IsAbstract, ua.VariantType.Boolean)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.MinimumSamplingInterval:
            nodedata.attributes[ua.AttributeIds.MinimumSamplingInterval] = AttributeValue(ua.DataValue(ua.Variant(item.MinimumSamplingInterval, ua.VariantType.Double)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.NodeClass:
            nodedata.attributes[ua.AttributeIds.NodeClass] = AttributeValue(ua.DataValue(ua.Variant(item.NodeClass, ua.VariantType.UInt32)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.NodeId:
            nodedata.attributes[ua.AttributeIds.NodeId] = AttributeValue(ua.DataValue(ua.Variant(item.NodeId, ua.VariantType.NodeId)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.Symmetric:
            nodedata.attributes[ua.AttributeIds.Symmetric] = AttributeValue(ua.DataValue(ua.Variant(item.Symmetric, ua.VariantType.Boolean)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.UserAccessLevel:
            nodedata.attributes[ua.AttributeIds.UserAccessLevel] = AttributeValue(ua.DataValue(ua.Variant(item.UserAccessLevel, ua.VariantType.Byte)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.UserExecutable:
            nodedata.attributes[ua.AttributeIds.UserExecutable] = AttributeValue(ua.DataValue(ua.Variant(item.UserExecutable, ua.VariantType.Boolean)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.UserWriteMask:
            nodedata.attributes[ua.AttributeIds.UserWriteMask] = AttributeValue(ua.DataValue(ua.Variant(item.UserWriteMask, ua.VariantType.Byte)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.ValueRank:
            nodedata.attributes[ua.AttributeIds.ValueRank] = AttributeValue(ua.DataValue(ua.Variant(item.ValueRank, ua.VariantType.Int32)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.WriteMask:
            nodedata.attributes[ua.AttributeIds.WriteMask] = AttributeValue(ua.DataValue(ua.Variant(item.WriteMask, ua.VariantType.Byte)))
        if item.SpecifiedAttributes & ua.NodeAttributesMask.Value:
            nodedata.attributes[ua.AttributeIds.Value] = AttributeValue(ua.DataValue(item.Value))

    def read(self, params):
        self.logger.debug("read %s", params)
        res = []
        for readvalue in params.NodesToRead:
            res.append(self.get_attribute_value(readvalue.NodeId, readvalue.AttributeId))
        print(res)
        return res

    def write(self, params):
        self.logger.debug("write %s", params)
        res = []
        for writevalue in params:
            res.append(self.set_attribute_value(writevalue.NodeId, writevalue.AttributeId, writevalue.Value))
        return res

    def browse(self, params):
        self.logger.debug("browse %s", params)
        res = []
        for desc in params.NodesToBrowse:
            res.append(self._browse(desc))
        return res

    def _browse(self, desc):
        res = ua.BrowseResult()
        if not desc.NodeId in self._nodes:
            res.StatusCode = ua.StatusCode(ua.StatusCodes.BadNodeIdInvalid)
            return res
        node = self._nodes[desc.NodeId]
        for ref in node.references:
            if not self._is_suitable_ref(desc, ref):
                continue
            res.References.append(ref)
        return res

    def _is_suitable_ref(self, desc, ref):
        if not self._suitable_direction(desc.BrowseDirection, ref.IsForward):
            self.logger.debug("%s is not suitable due to direction")
            return False
        if not self._suitable_reftype(desc.ReferenceTypeId, ref.ReferenceTypeId, desc.IncludeSubtypes):
            self.logger.debug("%s is not suitable due to type")
            return False
        if desc.NodeClassMask and ((desc.NodeClassMask & ref.NodeClass) == 0):
            self.logger.debug("%s is not suitable due to class")
            return False
        self.logger.debug("%s is a suitable ref for desc %s", ref, desc)
        return True



    def _suitable_reftype(self, ref1, ref2, subtypes):
        """
        """
        if not subtypes:
            return ref1.Identifier == ref2.Identifier
        oktype = self._get_sub_ref(ref1)
        #oktype = [node.Identifier for node in oktype]
        print("suitable types for ", ref1, " are ", oktype)
        print("ref2 is ", ref2)
        return ref2 in oktype

    def _get_sub_ref(self, ref):
        #print("lookin for ubstypes of", ref)
        res = []
        nodedata = self._nodes[ref]
        for ref in nodedata.references:
            #print("is ", ref, " suitable?")
            if ref.ReferenceTypeId.Identifier == ua.ObjectIds.HasSubtype:
                res.append(ref.NodeId)
                #print("OK ", ref, " is suitable")
                res += self._get_sub_ref(ref.NodeId)
        return res



    def _suitable_direction(self, desc, isforward):
        if desc == ua.BrowseDirection.Both:
            return True
        if desc == ua.BrowseDirection.Forward and isforward:
            return True
        return False





            
            
