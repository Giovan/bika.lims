# -*- coding: utf-8 -*-
#
# This file is part of Bika LIMS
#
# Copyright 2011-2017 by it's authors.
# Some rights reserved. See LICENSE.txt, AUTHORS.txt.

from bika.lims.idserver import renameAfterCreation
from bika.lims.utils import tmpID
from datetime import datetime
from Products.CMFPlone.utils import _createObjectByType
from magnitude import mg


def compare_containers(a, b):
    a_capacity = a.getCapacity().lower().split(" ", 1)
    b_capacity = b.getCapacity().lower().split(" ", 1)
    a_magnitude = mg(float(a_capacity[0]), a_capacity[1])
    b_magnitude = mg(float(b_capacity[0]), b_capacity[1])
    return cmp(
        a.getCapacity() and a_magnitude or mg(0, 'ml'),
        b.getCapacity() and b_magnitude or mg(0, 'ml')
    )


def set_container_preservation(context, container, data):
    # If container is pre-preserved, set the partition's preservation,
    # and flag the partition to be transitioned below.
    if container:
        if type(container) in (list, tuple):
            container = container[0]
        proxies = context.bika_setup_catalog(UID=container)
        container = [_p.getObject() for _p in proxies]
        container = container[0] if container else None
        if container:
            prepreserved = container.getPrePreserved()
            preservation = container.getPreservation()
            data['prepreserved'] = prepreserved
            if prepreserved and preservation:
                return preservation.UID()
    return data.get('preservation_uid', '')


def create_samplepartition(context, data, analyses=[]):
    """
    This function creates a partition object.
    :returns: a whole partition object
    :data: is a dictionary with some important data to create the partition,
    where the most important keys are: part_id and services
    {'part_id':xx, 'container_uid', xxxx, 'services': xxxx, 'part_id':xxx, ...}
    :analyses: A list of full object analyses
    """
    dummy = str(
             datetime.now()).replace(' ', '-').replace('.','').replace(':','')
    partition = _createObjectByType('SamplePartition', context, dummy)
    partition.unmarkCreationFlag()
    renameAfterCreation(partition)
    # Determine if the sampling workflow is enabled
    workflow_enabled = context.bika_setup.getSamplingWorkflowEnabled()
    # Sort containers and select smallest
    container = data.get('container_uid', None)
    if container:
        containers = []
        if type(container[0]) is str:
            # UIDs
            containers = context.bika_setup_catalog(UID=container)
            containers = [_p.getObject() for _p in containers]
        elif hasattr(container[0], 'getObject'):
            # Brains
            containers = [_p.getObject() for _p in container]
        elif hasattr(container[0], 'portal_type'):
            containers = [c for c in container]

        if containers:
            try: containers.sort(lambda a, b: compare_containers(a, b))
            except: pass
            container = containers[0]
    # Set the container and preservation
    preservation = set_container_preservation(context, container, data)
    # Add analyses
    partition_services = data['services']
    analyses = [a for a in analyses if a.getServiceUID() in partition_services]
    if analyses:
        partition.edit(Analyses=analyses)
    # Set some generated values
    partition.edit(
        Container=container,
        Preservation=preservation,
    )
    # Attach partition to analyses
    if analyses:
        for analysis in analyses:
            analysis.setSamplePartition(partition)
    # Perform the appropriate workflow action
    workflow_action = 'sampling_workflow' if workflow_enabled \
        else 'no_sampling_workflow'
    context.portal_workflow.doActionFor(partition, workflow_action)
    # Return the created partition
    return partition
