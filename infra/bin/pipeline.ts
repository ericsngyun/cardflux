#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { StorageStack } from '../lib/storage-stack';
import { CdnStack } from '../lib/cdn-stack';
import { PipelineStack } from '../lib/pipeline-stack';

const app = new cdk.App();

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};

const storageStack = new StorageStack(app, 'CardFluxStorageStack', { env });
const cdnStack = new CdnStack(app, 'CardFluxCdnStack', {
  env,
  bucket: storageStack.bucket,
});

new PipelineStack(app, 'CardFluxPipelineStack', {
  env,
  bucket: storageStack.bucket,
});
