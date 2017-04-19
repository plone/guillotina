# Persistence

There is three kind of objects that are considered on the system:


## Tree objects

Called Resources that implement guillotina.interfaces.IResource. This objects has a __name__ and a __parent__, fields that indicate the id on the tree and the link to the parent. By themselves they don't have access to the children they have, it needs to interact with the transaction object to get them.


## Nested

Objects that are linked at some attribute inside the Tree object, this object are serialized with the main object and may lead to conflicts if there is lots of this kind of objects.

It can belong to:

- A field that is an object


## Nested References

Base objects that belong to an specific object, its enough big to have its own entity and be saved in a different persistence object. Its not an element of the tree.

It can belong to:

- An annotation that is stored on a different object

- A BaseObject inherited field object
