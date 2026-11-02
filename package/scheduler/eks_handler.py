# -*- coding: utf-8 -*-

"""eks service scheduler."""

import os
from typing import Dict, List

import boto3

from botocore.exceptions import ClientError

from scheduler.exceptions import eks_exception
from scheduler.filter_resources_by_tags import FilterByTags


def _scaling_config(env_var: str) -> Dict[str, int]:
    """Read an eks nodegroup scaling config from an environment variable.

    :param str env_var:
        Name of an environment variable holding "minSize,maxSize,desiredSize".

    :return dict:
        Scaling config accepted by eks update_nodegroup_config.
    """
    value = os.getenv(env_var)
    if not value:
        raise ValueError(f"Environment variable {env_var} is not set")
    sizes = [int(size) for size in value.split(",")]
    if len(sizes) != 3:
        raise ValueError(
            f"{env_var} must be 'minSize,maxSize,desiredSize', got {value!r}"
        )
    return {"minSize": sizes[0], "maxSize": sizes[1], "desiredSize": sizes[2]}


class EksScheduler(object):
    """Abstract eks Service scheduler in a class."""

    def __init__(self, region_name=None) -> None:
        """Initialize eks service scheduler."""
        if region_name:
            self.eks = boto3.client("eks", region_name=region_name)
        else:
            self.eks = boto3.client("eks")
        self.tag_api = FilterByTags(region_name=region_name)

    def stop(self, aws_tags: List[Dict]) -> None:
        """Aws eks nodegroup stop function.

        Scale down eks nodegroups with defined tags to the sizes set
        in the EKS_CONFIG_PAUSED environment variable.

        :param list[map] aws_tags:
            Aws tags to use for filter resources.
            For example:
            [
                {
                    'Key': 'string',
                    'Values': [
                        'string',
                    ]
                }
            ]
        """
        print("Inside the EKS stop")
        for service_arn in self.tag_api.get_resources("eks:nodegroup", aws_tags):
            nodegroup_name = service_arn.split("/")[-2]
            cluster_name = service_arn.split("/")[-3]
            print(f"Scaling down {cluster_name}, nodegroup_name {nodegroup_name}")
            scaling_config = _scaling_config("EKS_CONFIG_PAUSED")
            print(f"Scaling config: {scaling_config}")
            try:
                print("About to try the update")
                self.eks.update_nodegroup_config(
                    clusterName=cluster_name,
                    nodegroupName=nodegroup_name,
                    scalingConfig=scaling_config,
                )
                print("Completed the update")
            except ClientError as exc:
                eks_exception("eks Service", service_arn, exc)

    def start(self, aws_tags: List[Dict]) -> None:
        """Aws eks nodegroup start function.

        Scale up eks nodegroups with defined tags to the sizes set
        in the EKS_CONFIG_RESUME environment variable.

        :param list[map] aws_tags:
            Aws tags to use for filter resources.
            For example:
            [
                {
                    'Key': 'string',
                    'Values': [
                        'string',
                    ]
                }
            ]
        """
        for service_arn in self.tag_api.get_resources("eks:nodegroup", aws_tags):
            print(f"Service ARN is {service_arn}")
            nodegroup_name = service_arn.split("/")[-2]
            cluster_name = service_arn.split("/")[-3]
            print(f"Cluster name is {cluster_name}, nodegroup_name is {nodegroup_name}")
            scaling_config = _scaling_config("EKS_CONFIG_RESUME")
            print(f"Scaling config: {scaling_config}")
            try:
                print("About to try the update")
                self.eks.update_nodegroup_config(
                    clusterName=cluster_name,
                    nodegroupName=nodegroup_name,
                    scalingConfig=scaling_config,
                )
                print("Completed the update")
            except ClientError as exc:
                eks_exception("eks Service", service_arn, exc)
