import * as cdk from 'aws-cdk-lib';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface PipelineStackProps extends cdk.StackProps {
  bucket: s3.Bucket;
}

export class PipelineStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: PipelineStackProps) {
    super(scope, id, props);

    // CodeBuild project for running the pipeline
    const buildProject = new codebuild.PipelineProject(this, 'CardFluxBuild', {
      projectName: 'CardFluxPipeline',
      environment: {
        buildImage: codebuild.LinuxBuildImage.STANDARD_7_0,
        computeType: codebuild.ComputeType.LARGE,
        privileged: true,
      },
      buildSpec: codebuild.BuildSpec.fromObject({
        version: '0.2',
        phases: {
          install: {
            commands: [
              'echo Installing dependencies...',
              'npm install -g pnpm',
              'pnpm install',
              'pip install --upgrade pip',
              'cd services/embedder && pip install -r requirements.txt',
              'cd ../indexer && pip install -r requirements.txt',
              'cd ../..',
            ],
          },
          build: {
            commands: [
              'echo Running pipeline...',
              'node scripts/make/run-pipeline.mjs',
            ],
          },
          post_build: {
            commands: [
              'echo Uploading artifacts to S3...',
              `aws s3 sync artifacts/ s3://${props.bucket.bucketName}/artifacts/ --delete`,
            ],
          },
        },
        artifacts: {
          files: ['**/*'],
          'base-directory': 'artifacts',
        },
      }),
      timeout: cdk.Duration.hours(3),
    });

    // Grant S3 permissions
    props.bucket.grantReadWrite(buildProject);

    // Add additional permissions for the build project
    buildProject.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['s3:ListBucket'],
        resources: [props.bucket.bucketArn],
      })
    );

    // Create artifact bucket for pipeline
    const artifactBucket = new s3.Bucket(this, 'PipelineArtifacts', {
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // CodePipeline
    const sourceOutput = new codepipeline.Artifact();
    const buildOutput = new codepipeline.Artifact();

    new codepipeline.Pipeline(this, 'Pipeline', {
      pipelineName: 'CardFluxPipeline',
      artifactBucket,
      stages: [
        {
          stageName: 'Source',
          actions: [
            new codepipeline_actions.S3SourceAction({
              actionName: 'S3Source',
              bucket: props.bucket,
              bucketKey: 'trigger/pipeline.zip',
              output: sourceOutput,
              trigger: codepipeline_actions.S3Trigger.EVENTS,
            }),
          ],
        },
        {
          stageName: 'Build',
          actions: [
            new codepipeline_actions.CodeBuildAction({
              actionName: 'RunPipeline',
              project: buildProject,
              input: sourceOutput,
              outputs: [buildOutput],
            }),
          ],
        },
      ],
    });
  }
}
