@0x{{obj._capnp_id}};

#{{obj.url}}
struct Schema {

    {% for prop in obj.properties %}
    #{{prop.name}}
    {{prop.capnp_schema}}
    {% endfor %}

    {% for prop in obj.lists %}
    {{prop.capnp_schema}}
    {% endfor %}


}
