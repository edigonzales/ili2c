from ili2c.pyili2c.metamodel import (
    Attribute,
    Cardinality,
    ListType,
    Model,
    Table,
    Topic,
    TransferDescription,
    Type,
    Viewable,
)


def test_scoped_names_and_lookup():
    td = TransferDescription()
    model = Model("TestModel", schema_language="ili2_4", schema_version="2.4")
    td.add_model(model)

    topic = Topic("TestTopic")
    model.add_topic(topic)

    table = Table("ClassA", kind="CLASS")
    topic.add_class(table)

    attribute = Attribute("name", Type("TEXT"))
    table.add_attribute(attribute)

    assert isinstance(table, Viewable)
    assert table.getScopedName() == "TestModel.TestTopic.ClassA"
    assert attribute.getScopedName() == "TestModel.TestTopic.ClassA.name"
    assert td.find_model("TestModel") is model


def test_list_type_cardinality():
    element_type = Type("TestModel.StructA")
    cardinality = Cardinality(0, -1)
    list_type = ListType(element_type, is_bag=False, cardinality=cardinality)

    assert list_type.getElementType() is element_type
    assert list_type.cardinality_min == 0
    assert list_type.cardinality_max == -1
    assert list_type.isBag() is False
