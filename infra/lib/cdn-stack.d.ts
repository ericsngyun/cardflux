import * as cdk from 'aws-cdk-lib';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';
export interface CdnStackProps extends cdk.StackProps {
    bucket: s3.Bucket;
}
export declare class CdnStack extends cdk.Stack {
    readonly distribution: cloudfront.Distribution;
    constructor(scope: Construct, id: string, props: CdnStackProps);
}
