from pyili2c.metamodel import (
    AttributeDef,
    Cardinality,
    EnumerationType,
    Model,
    Table,
    Topic,
    TransferDescription,
    Type,
)


def test_scoped_names_and_lookup():
    td = TransferDescription()
    model = Model("TestModel")
    model.setFileName("TestModel.ili")
    td.add_model(model)

    topic = Topic("TestTopic")
    model.add_topic(topic)

    table = Table("ClassA")
    topic.add_class(table)

    attr = AttributeDef("attr")
    attr.setDomain(Type("TEXT"))
    attr.setCardinality(Cardinality(0, 1))
    table.add_attribute(attr)

    assert table.getScopedName() == "TestModel.TestTopic.ClassA"
    assert attr.getScopedName() == "TestModel.TestTopic.ClassA.attr"
    assert td.find_model("TestModel") is model
    assert td.getModelsFromLastFile() == [model]


def test_boolean_domain_detection():
    enum_type = EnumerationType("BooleanDomain", is_boolean=True)
    attr = AttributeDef("flag")
    attr.setDomain(enum_type)

    assert attr.isDomainBoolean() is True
