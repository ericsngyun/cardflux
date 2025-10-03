import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
export interface PipelineStackProps extends cdk.StackProps {
    bucket: s3.Bucket;
}
export declare class PipelineStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: PipelineStackProps);
}
