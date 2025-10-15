# Generated from grammars-antlr4/InterlisParserPy.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .InterlisParserPy import InterlisParserPy
else:
    from InterlisParserPy import InterlisParserPy

# This class defines a complete generic visitor for a parse tree produced by InterlisParserPy.

class InterlisParserPyVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by InterlisParserPy#interlis2def.
    def visitInterlis2def(self, ctx:InterlisParserPy.Interlis2defContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#modeldef.
    def visitModeldef(self, ctx:InterlisParserPy.ModeldefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#topicDef.
    def visitTopicDef(self, ctx:InterlisParserPy.TopicDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#definitions.
    def visitDefinitions(self, ctx:InterlisParserPy.DefinitionsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#topicRef.
    def visitTopicRef(self, ctx:InterlisParserPy.TopicRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#genericRef.
    def visitGenericRef(self, ctx:InterlisParserPy.GenericRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#classDef.
    def visitClassDef(self, ctx:InterlisParserPy.ClassDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#structureDef.
    def visitStructureDef(self, ctx:InterlisParserPy.StructureDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#classRef.
    def visitClassRef(self, ctx:InterlisParserPy.ClassRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#classOrStructureDef.
    def visitClassOrStructureDef(self, ctx:InterlisParserPy.ClassOrStructureDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#structureRef.
    def visitStructureRef(self, ctx:InterlisParserPy.StructureRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#classOrStructureRef.
    def visitClassOrStructureRef(self, ctx:InterlisParserPy.ClassOrStructureRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#attributeDef.
    def visitAttributeDef(self, ctx:InterlisParserPy.AttributeDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#attrTypeDef.
    def visitAttrTypeDef(self, ctx:InterlisParserPy.AttrTypeDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#attrType.
    def visitAttrType(self, ctx:InterlisParserPy.AttrTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#referenceAttr.
    def visitReferenceAttr(self, ctx:InterlisParserPy.ReferenceAttrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#restrictedClassOrAssRef.
    def visitRestrictedClassOrAssRef(self, ctx:InterlisParserPy.RestrictedClassOrAssRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#classOrAssociationRef.
    def visitClassOrAssociationRef(self, ctx:InterlisParserPy.ClassOrAssociationRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#restrictedStructureRef.
    def visitRestrictedStructureRef(self, ctx:InterlisParserPy.RestrictedStructureRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#restrictedClassOrStructureRef.
    def visitRestrictedClassOrStructureRef(self, ctx:InterlisParserPy.RestrictedClassOrStructureRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#associationDef.
    def visitAssociationDef(self, ctx:InterlisParserPy.AssociationDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#associationRef.
    def visitAssociationRef(self, ctx:InterlisParserPy.AssociationRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#roleDef.
    def visitRoleDef(self, ctx:InterlisParserPy.RoleDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#cardinality.
    def visitCardinality(self, ctx:InterlisParserPy.CardinalityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#domainDef.
    def visitDomainDef(self, ctx:InterlisParserPy.DomainDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#iliType.
    def visitIliType(self, ctx:InterlisParserPy.IliTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#domainRef.
    def visitDomainRef(self, ctx:InterlisParserPy.DomainRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#baseType.
    def visitBaseType(self, ctx:InterlisParserPy.BaseTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#constant.
    def visitConstant(self, ctx:InterlisParserPy.ConstantContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#textType.
    def visitTextType(self, ctx:InterlisParserPy.TextTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#textConst.
    def visitTextConst(self, ctx:InterlisParserPy.TextConstContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#enumerationType.
    def visitEnumerationType(self, ctx:InterlisParserPy.EnumerationTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#enumTreeValueType.
    def visitEnumTreeValueType(self, ctx:InterlisParserPy.EnumTreeValueTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#enumeration.
    def visitEnumeration(self, ctx:InterlisParserPy.EnumerationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#enumElement.
    def visitEnumElement(self, ctx:InterlisParserPy.EnumElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#enumerationConst.
    def visitEnumerationConst(self, ctx:InterlisParserPy.EnumerationConstContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#alignmentType.
    def visitAlignmentType(self, ctx:InterlisParserPy.AlignmentTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#booleanType.
    def visitBooleanType(self, ctx:InterlisParserPy.BooleanTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#numeric.
    def visitNumeric(self, ctx:InterlisParserPy.NumericContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#numericType.
    def visitNumericType(self, ctx:InterlisParserPy.NumericTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#refSys.
    def visitRefSys(self, ctx:InterlisParserPy.RefSysContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#decConst.
    def visitDecConst(self, ctx:InterlisParserPy.DecConstContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#numericConst.
    def visitNumericConst(self, ctx:InterlisParserPy.NumericConstContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#formattedType.
    def visitFormattedType(self, ctx:InterlisParserPy.FormattedTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#formatDef.
    def visitFormatDef(self, ctx:InterlisParserPy.FormatDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#baseAttrRef.
    def visitBaseAttrRef(self, ctx:InterlisParserPy.BaseAttrRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#formattedConst.
    def visitFormattedConst(self, ctx:InterlisParserPy.FormattedConstContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#dateTimeType.
    def visitDateTimeType(self, ctx:InterlisParserPy.DateTimeTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#coordinateType.
    def visitCoordinateType(self, ctx:InterlisParserPy.CoordinateTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#rotationDef.
    def visitRotationDef(self, ctx:InterlisParserPy.RotationDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#contextDef.
    def visitContextDef(self, ctx:InterlisParserPy.ContextDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#oIDType.
    def visitOIDType(self, ctx:InterlisParserPy.OIDTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#blackboxType.
    def visitBlackboxType(self, ctx:InterlisParserPy.BlackboxTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#classType.
    def visitClassType(self, ctx:InterlisParserPy.ClassTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#attributeType.
    def visitAttributeType(self, ctx:InterlisParserPy.AttributeTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#classConst.
    def visitClassConst(self, ctx:InterlisParserPy.ClassConstContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#attributePathConst.
    def visitAttributePathConst(self, ctx:InterlisParserPy.AttributePathConstContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#lineType.
    def visitLineType(self, ctx:InterlisParserPy.LineTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#lineForm.
    def visitLineForm(self, ctx:InterlisParserPy.LineFormContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#lineFormType.
    def visitLineFormType(self, ctx:InterlisParserPy.LineFormTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#controlPoints.
    def visitControlPoints(self, ctx:InterlisParserPy.ControlPointsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#intersectionDef.
    def visitIntersectionDef(self, ctx:InterlisParserPy.IntersectionDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#lineFormTypeDef.
    def visitLineFormTypeDef(self, ctx:InterlisParserPy.LineFormTypeDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#unitDef.
    def visitUnitDef(self, ctx:InterlisParserPy.UnitDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#derivedUnit.
    def visitDerivedUnit(self, ctx:InterlisParserPy.DerivedUnitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#composedUnit.
    def visitComposedUnit(self, ctx:InterlisParserPy.ComposedUnitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#unitRef.
    def visitUnitRef(self, ctx:InterlisParserPy.UnitRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#metaDataBasketDef.
    def visitMetaDataBasketDef(self, ctx:InterlisParserPy.MetaDataBasketDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#metaDataBasketRef.
    def visitMetaDataBasketRef(self, ctx:InterlisParserPy.MetaDataBasketRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#metaObjectRef.
    def visitMetaObjectRef(self, ctx:InterlisParserPy.MetaObjectRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#parameterDef.
    def visitParameterDef(self, ctx:InterlisParserPy.ParameterDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#runTimeParameterDef.
    def visitRunTimeParameterDef(self, ctx:InterlisParserPy.RunTimeParameterDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#constraintDef.
    def visitConstraintDef(self, ctx:InterlisParserPy.ConstraintDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#mandatoryConstraint.
    def visitMandatoryConstraint(self, ctx:InterlisParserPy.MandatoryConstraintContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#plausibilityConstraint.
    def visitPlausibilityConstraint(self, ctx:InterlisParserPy.PlausibilityConstraintContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#existenceConstraint.
    def visitExistenceConstraint(self, ctx:InterlisParserPy.ExistenceConstraintContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#uniquenessConstraint.
    def visitUniquenessConstraint(self, ctx:InterlisParserPy.UniquenessConstraintContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#globalUniqueness.
    def visitGlobalUniqueness(self, ctx:InterlisParserPy.GlobalUniquenessContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#uniqueEl.
    def visitUniqueEl(self, ctx:InterlisParserPy.UniqueElContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#localUniqueness.
    def visitLocalUniqueness(self, ctx:InterlisParserPy.LocalUniquenessContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#setConstraint.
    def visitSetConstraint(self, ctx:InterlisParserPy.SetConstraintContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#constraintsDef.
    def visitConstraintsDef(self, ctx:InterlisParserPy.ConstraintsDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#expression.
    def visitExpression(self, ctx:InterlisParserPy.ExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#term.
    def visitTerm(self, ctx:InterlisParserPy.TermContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#term0.
    def visitTerm0(self, ctx:InterlisParserPy.Term0Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#term1.
    def visitTerm1(self, ctx:InterlisParserPy.Term1Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#term2.
    def visitTerm2(self, ctx:InterlisParserPy.Term2Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#predicate.
    def visitPredicate(self, ctx:InterlisParserPy.PredicateContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#relation.
    def visitRelation(self, ctx:InterlisParserPy.RelationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#factor.
    def visitFactor(self, ctx:InterlisParserPy.FactorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#objectOrAttributePath.
    def visitObjectOrAttributePath(self, ctx:InterlisParserPy.ObjectOrAttributePathContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#attributePath.
    def visitAttributePath(self, ctx:InterlisParserPy.AttributePathContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#pathEl.
    def visitPathEl(self, ctx:InterlisParserPy.PathElContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#associationPath.
    def visitAssociationPath(self, ctx:InterlisParserPy.AssociationPathContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#attributeRef.
    def visitAttributeRef(self, ctx:InterlisParserPy.AttributeRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#functionCall.
    def visitFunctionCall(self, ctx:InterlisParserPy.FunctionCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#argument.
    def visitArgument(self, ctx:InterlisParserPy.ArgumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#functionDecl.
    def visitFunctionDecl(self, ctx:InterlisParserPy.FunctionDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#functionDef.
    def visitFunctionDef(self, ctx:InterlisParserPy.FunctionDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#argumentDef.
    def visitArgumentDef(self, ctx:InterlisParserPy.ArgumentDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#argumentType.
    def visitArgumentType(self, ctx:InterlisParserPy.ArgumentTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#viewDef.
    def visitViewDef(self, ctx:InterlisParserPy.ViewDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#viewRef.
    def visitViewRef(self, ctx:InterlisParserPy.ViewRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#formationDef.
    def visitFormationDef(self, ctx:InterlisParserPy.FormationDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#projection.
    def visitProjection(self, ctx:InterlisParserPy.ProjectionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#join.
    def visitJoin(self, ctx:InterlisParserPy.JoinContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#union.
    def visitUnion(self, ctx:InterlisParserPy.UnionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#aggregation.
    def visitAggregation(self, ctx:InterlisParserPy.AggregationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#inspection.
    def visitInspection(self, ctx:InterlisParserPy.InspectionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#renamedViewableRef.
    def visitRenamedViewableRef(self, ctx:InterlisParserPy.RenamedViewableRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#viewableRef.
    def visitViewableRef(self, ctx:InterlisParserPy.ViewableRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#baseExtensionDef.
    def visitBaseExtensionDef(self, ctx:InterlisParserPy.BaseExtensionDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#selection.
    def visitSelection(self, ctx:InterlisParserPy.SelectionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#viewAttributes.
    def visitViewAttributes(self, ctx:InterlisParserPy.ViewAttributesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#graphicDef.
    def visitGraphicDef(self, ctx:InterlisParserPy.GraphicDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#graphicRef.
    def visitGraphicRef(self, ctx:InterlisParserPy.GraphicRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#drawingRule.
    def visitDrawingRule(self, ctx:InterlisParserPy.DrawingRuleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#condSignParamAssignment.
    def visitCondSignParamAssignment(self, ctx:InterlisParserPy.CondSignParamAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#signParamAssignment.
    def visitSignParamAssignment(self, ctx:InterlisParserPy.SignParamAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#enumAssignment.
    def visitEnumAssignment(self, ctx:InterlisParserPy.EnumAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by InterlisParserPy#enumRange.
    def visitEnumRange(self, ctx:InterlisParserPy.EnumRangeContext):
        return self.visitChildren(ctx)



del InterlisParserPy