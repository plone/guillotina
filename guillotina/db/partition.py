from guillotina.interfaces import IContainer


class DefaultPartitioner:
    '''
    - sql(against dynamic tables)
    - insert is only thing that needs to check for new tables to be created
    - partitioning can only be done on a leaf once
    - root still needs to know part id; however, inserts go to partitioned table
    - partitioned objects
    '''
    part_id = 0
    root = False

    def __init__(self, context):
        self.context = context


class ContainerPartitioner(DefaultPartitioner):

    @property
    def root(self) -> bool:
        return IContainer.providedBy(self.context)

    @property
    def part_id(self) -> int:
        if self.context.__of__:
            context = self.context.__of__
        else:
            context = self.context
        while context is not None and not IContainer.providedBy(context):
            context = context.__parent__
        if context is not None:
            # fast way to calculate, unlikely to produce collisions(but can)
            return sum([ord(v) for v in context._p_oid])
        return 0
