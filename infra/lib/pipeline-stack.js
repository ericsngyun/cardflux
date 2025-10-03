"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.PipelineStack = void 0;
const cdk = __importStar(require("aws-cdk-lib"));
const codebuild = __importStar(require("aws-cdk-lib/aws-codebuild"));
const codepipeline = __importStar(require("aws-cdk-lib/aws-codepipeline"));
const codepipeline_actions = __importStar(require("aws-cdk-lib/aws-codepipeline-actions"));
const s3 = __importStar(require("aws-cdk-lib/aws-s3"));
const iam = __importStar(require("aws-cdk-lib/aws-iam"));
class PipelineStack extends cdk.Stack {
    constructor(scope, id, props) {
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
        buildProject.addToRolePolicy(new iam.PolicyStatement({
            actions: ['s3:ListBucket'],
            resources: [props.bucket.bucketArn],
        }));
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
exports.PipelineStack = PipelineStack;
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoicGlwZWxpbmUtc3RhY2suanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyJwaXBlbGluZS1zdGFjay50cyJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFBQSxpREFBbUM7QUFDbkMscUVBQXVEO0FBQ3ZELDJFQUE2RDtBQUM3RCwyRkFBNkU7QUFDN0UsdURBQXlDO0FBQ3pDLHlEQUEyQztBQU8zQyxNQUFhLGFBQWMsU0FBUSxHQUFHLENBQUMsS0FBSztJQUMxQyxZQUFZLEtBQWdCLEVBQUUsRUFBVSxFQUFFLEtBQXlCO1FBQ2pFLEtBQUssQ0FBQyxLQUFLLEVBQUUsRUFBRSxFQUFFLEtBQUssQ0FBQyxDQUFDO1FBRXhCLDZDQUE2QztRQUM3QyxNQUFNLFlBQVksR0FBRyxJQUFJLFNBQVMsQ0FBQyxlQUFlLENBQUMsSUFBSSxFQUFFLGVBQWUsRUFBRTtZQUN4RSxXQUFXLEVBQUUsa0JBQWtCO1lBQy9CLFdBQVcsRUFBRTtnQkFDWCxVQUFVLEVBQUUsU0FBUyxDQUFDLGVBQWUsQ0FBQyxZQUFZO2dCQUNsRCxXQUFXLEVBQUUsU0FBUyxDQUFDLFdBQVcsQ0FBQyxLQUFLO2dCQUN4QyxVQUFVLEVBQUUsSUFBSTthQUNqQjtZQUNELFNBQVMsRUFBRSxTQUFTLENBQUMsU0FBUyxDQUFDLFVBQVUsQ0FBQztnQkFDeEMsT0FBTyxFQUFFLEtBQUs7Z0JBQ2QsTUFBTSxFQUFFO29CQUNOLE9BQU8sRUFBRTt3QkFDUCxRQUFRLEVBQUU7NEJBQ1IsaUNBQWlDOzRCQUNqQyxxQkFBcUI7NEJBQ3JCLGNBQWM7NEJBQ2QsMkJBQTJCOzRCQUMzQix5REFBeUQ7NEJBQ3pELGtEQUFrRDs0QkFDbEQsVUFBVTt5QkFDWDtxQkFDRjtvQkFDRCxLQUFLLEVBQUU7d0JBQ0wsUUFBUSxFQUFFOzRCQUNSLDBCQUEwQjs0QkFDMUIsb0NBQW9DO3lCQUNyQztxQkFDRjtvQkFDRCxVQUFVLEVBQUU7d0JBQ1YsUUFBUSxFQUFFOzRCQUNSLG1DQUFtQzs0QkFDbkMsK0JBQStCLEtBQUssQ0FBQyxNQUFNLENBQUMsVUFBVSxzQkFBc0I7eUJBQzdFO3FCQUNGO2lCQUNGO2dCQUNELFNBQVMsRUFBRTtvQkFDVCxLQUFLLEVBQUUsQ0FBQyxNQUFNLENBQUM7b0JBQ2YsZ0JBQWdCLEVBQUUsV0FBVztpQkFDOUI7YUFDRixDQUFDO1lBQ0YsT0FBTyxFQUFFLEdBQUcsQ0FBQyxRQUFRLENBQUMsS0FBSyxDQUFDLENBQUMsQ0FBQztTQUMvQixDQUFDLENBQUM7UUFFSCx1QkFBdUI7UUFDdkIsS0FBSyxDQUFDLE1BQU0sQ0FBQyxjQUFjLENBQUMsWUFBWSxDQUFDLENBQUM7UUFFMUMsbURBQW1EO1FBQ25ELFlBQVksQ0FBQyxlQUFlLENBQzFCLElBQUksR0FBRyxDQUFDLGVBQWUsQ0FBQztZQUN0QixPQUFPLEVBQUUsQ0FBQyxlQUFlLENBQUM7WUFDMUIsU0FBUyxFQUFFLENBQUMsS0FBSyxDQUFDLE1BQU0sQ0FBQyxTQUFTLENBQUM7U0FDcEMsQ0FBQyxDQUNILENBQUM7UUFFRixzQ0FBc0M7UUFDdEMsTUFBTSxjQUFjLEdBQUcsSUFBSSxFQUFFLENBQUMsTUFBTSxDQUFDLElBQUksRUFBRSxtQkFBbUIsRUFBRTtZQUM5RCxhQUFhLEVBQUUsR0FBRyxDQUFDLGFBQWEsQ0FBQyxPQUFPO1lBQ3hDLGlCQUFpQixFQUFFLElBQUk7U0FDeEIsQ0FBQyxDQUFDO1FBRUgsZUFBZTtRQUNmLE1BQU0sWUFBWSxHQUFHLElBQUksWUFBWSxDQUFDLFFBQVEsRUFBRSxDQUFDO1FBQ2pELE1BQU0sV0FBVyxHQUFHLElBQUksWUFBWSxDQUFDLFFBQVEsRUFBRSxDQUFDO1FBRWhELElBQUksWUFBWSxDQUFDLFFBQVEsQ0FBQyxJQUFJLEVBQUUsVUFBVSxFQUFFO1lBQzFDLFlBQVksRUFBRSxrQkFBa0I7WUFDaEMsY0FBYztZQUNkLE1BQU0sRUFBRTtnQkFDTjtvQkFDRSxTQUFTLEVBQUUsUUFBUTtvQkFDbkIsT0FBTyxFQUFFO3dCQUNQLElBQUksb0JBQW9CLENBQUMsY0FBYyxDQUFDOzRCQUN0QyxVQUFVLEVBQUUsVUFBVTs0QkFDdEIsTUFBTSxFQUFFLEtBQUssQ0FBQyxNQUFNOzRCQUNwQixTQUFTLEVBQUUsc0JBQXNCOzRCQUNqQyxNQUFNLEVBQUUsWUFBWTs0QkFDcEIsT0FBTyxFQUFFLG9CQUFvQixDQUFDLFNBQVMsQ0FBQyxNQUFNO3lCQUMvQyxDQUFDO3FCQUNIO2lCQUNGO2dCQUNEO29CQUNFLFNBQVMsRUFBRSxPQUFPO29CQUNsQixPQUFPLEVBQUU7d0JBQ1AsSUFBSSxvQkFBb0IsQ0FBQyxlQUFlLENBQUM7NEJBQ3ZDLFVBQVUsRUFBRSxhQUFhOzRCQUN6QixPQUFPLEVBQUUsWUFBWTs0QkFDckIsS0FBSyxFQUFFLFlBQVk7NEJBQ25CLE9BQU8sRUFBRSxDQUFDLFdBQVcsQ0FBQzt5QkFDdkIsQ0FBQztxQkFDSDtpQkFDRjthQUNGO1NBQ0YsQ0FBQyxDQUFDO0lBQ0wsQ0FBQztDQUNGO0FBbEdELHNDQWtHQyIsInNvdXJjZXNDb250ZW50IjpbImltcG9ydCAqIGFzIGNkayBmcm9tICdhd3MtY2RrLWxpYic7XG5pbXBvcnQgKiBhcyBjb2RlYnVpbGQgZnJvbSAnYXdzLWNkay1saWIvYXdzLWNvZGVidWlsZCc7XG5pbXBvcnQgKiBhcyBjb2RlcGlwZWxpbmUgZnJvbSAnYXdzLWNkay1saWIvYXdzLWNvZGVwaXBlbGluZSc7XG5pbXBvcnQgKiBhcyBjb2RlcGlwZWxpbmVfYWN0aW9ucyBmcm9tICdhd3MtY2RrLWxpYi9hd3MtY29kZXBpcGVsaW5lLWFjdGlvbnMnO1xuaW1wb3J0ICogYXMgczMgZnJvbSAnYXdzLWNkay1saWIvYXdzLXMzJztcbmltcG9ydCAqIGFzIGlhbSBmcm9tICdhd3MtY2RrLWxpYi9hd3MtaWFtJztcbmltcG9ydCB7IENvbnN0cnVjdCB9IGZyb20gJ2NvbnN0cnVjdHMnO1xuXG5leHBvcnQgaW50ZXJmYWNlIFBpcGVsaW5lU3RhY2tQcm9wcyBleHRlbmRzIGNkay5TdGFja1Byb3BzIHtcbiAgYnVja2V0OiBzMy5CdWNrZXQ7XG59XG5cbmV4cG9ydCBjbGFzcyBQaXBlbGluZVN0YWNrIGV4dGVuZHMgY2RrLlN0YWNrIHtcbiAgY29uc3RydWN0b3Ioc2NvcGU6IENvbnN0cnVjdCwgaWQ6IHN0cmluZywgcHJvcHM6IFBpcGVsaW5lU3RhY2tQcm9wcykge1xuICAgIHN1cGVyKHNjb3BlLCBpZCwgcHJvcHMpO1xuXG4gICAgLy8gQ29kZUJ1aWxkIHByb2plY3QgZm9yIHJ1bm5pbmcgdGhlIHBpcGVsaW5lXG4gICAgY29uc3QgYnVpbGRQcm9qZWN0ID0gbmV3IGNvZGVidWlsZC5QaXBlbGluZVByb2plY3QodGhpcywgJ0NhcmRGbHV4QnVpbGQnLCB7XG4gICAgICBwcm9qZWN0TmFtZTogJ0NhcmRGbHV4UGlwZWxpbmUnLFxuICAgICAgZW52aXJvbm1lbnQ6IHtcbiAgICAgICAgYnVpbGRJbWFnZTogY29kZWJ1aWxkLkxpbnV4QnVpbGRJbWFnZS5TVEFOREFSRF83XzAsXG4gICAgICAgIGNvbXB1dGVUeXBlOiBjb2RlYnVpbGQuQ29tcHV0ZVR5cGUuTEFSR0UsXG4gICAgICAgIHByaXZpbGVnZWQ6IHRydWUsXG4gICAgICB9LFxuICAgICAgYnVpbGRTcGVjOiBjb2RlYnVpbGQuQnVpbGRTcGVjLmZyb21PYmplY3Qoe1xuICAgICAgICB2ZXJzaW9uOiAnMC4yJyxcbiAgICAgICAgcGhhc2VzOiB7XG4gICAgICAgICAgaW5zdGFsbDoge1xuICAgICAgICAgICAgY29tbWFuZHM6IFtcbiAgICAgICAgICAgICAgJ2VjaG8gSW5zdGFsbGluZyBkZXBlbmRlbmNpZXMuLi4nLFxuICAgICAgICAgICAgICAnbnBtIGluc3RhbGwgLWcgcG5wbScsXG4gICAgICAgICAgICAgICdwbnBtIGluc3RhbGwnLFxuICAgICAgICAgICAgICAncGlwIGluc3RhbGwgLS11cGdyYWRlIHBpcCcsXG4gICAgICAgICAgICAgICdjZCBzZXJ2aWNlcy9lbWJlZGRlciAmJiBwaXAgaW5zdGFsbCAtciByZXF1aXJlbWVudHMudHh0JyxcbiAgICAgICAgICAgICAgJ2NkIC4uL2luZGV4ZXIgJiYgcGlwIGluc3RhbGwgLXIgcmVxdWlyZW1lbnRzLnR4dCcsXG4gICAgICAgICAgICAgICdjZCAuLi8uLicsXG4gICAgICAgICAgICBdLFxuICAgICAgICAgIH0sXG4gICAgICAgICAgYnVpbGQ6IHtcbiAgICAgICAgICAgIGNvbW1hbmRzOiBbXG4gICAgICAgICAgICAgICdlY2hvIFJ1bm5pbmcgcGlwZWxpbmUuLi4nLFxuICAgICAgICAgICAgICAnbm9kZSBzY3JpcHRzL21ha2UvcnVuLXBpcGVsaW5lLm1qcycsXG4gICAgICAgICAgICBdLFxuICAgICAgICAgIH0sXG4gICAgICAgICAgcG9zdF9idWlsZDoge1xuICAgICAgICAgICAgY29tbWFuZHM6IFtcbiAgICAgICAgICAgICAgJ2VjaG8gVXBsb2FkaW5nIGFydGlmYWN0cyB0byBTMy4uLicsXG4gICAgICAgICAgICAgIGBhd3MgczMgc3luYyBhcnRpZmFjdHMvIHMzOi8vJHtwcm9wcy5idWNrZXQuYnVja2V0TmFtZX0vYXJ0aWZhY3RzLyAtLWRlbGV0ZWAsXG4gICAgICAgICAgICBdLFxuICAgICAgICAgIH0sXG4gICAgICAgIH0sXG4gICAgICAgIGFydGlmYWN0czoge1xuICAgICAgICAgIGZpbGVzOiBbJyoqLyonXSxcbiAgICAgICAgICAnYmFzZS1kaXJlY3RvcnknOiAnYXJ0aWZhY3RzJyxcbiAgICAgICAgfSxcbiAgICAgIH0pLFxuICAgICAgdGltZW91dDogY2RrLkR1cmF0aW9uLmhvdXJzKDMpLFxuICAgIH0pO1xuXG4gICAgLy8gR3JhbnQgUzMgcGVybWlzc2lvbnNcbiAgICBwcm9wcy5idWNrZXQuZ3JhbnRSZWFkV3JpdGUoYnVpbGRQcm9qZWN0KTtcblxuICAgIC8vIEFkZCBhZGRpdGlvbmFsIHBlcm1pc3Npb25zIGZvciB0aGUgYnVpbGQgcHJvamVjdFxuICAgIGJ1aWxkUHJvamVjdC5hZGRUb1JvbGVQb2xpY3koXG4gICAgICBuZXcgaWFtLlBvbGljeVN0YXRlbWVudCh7XG4gICAgICAgIGFjdGlvbnM6IFsnczM6TGlzdEJ1Y2tldCddLFxuICAgICAgICByZXNvdXJjZXM6IFtwcm9wcy5idWNrZXQuYnVja2V0QXJuXSxcbiAgICAgIH0pXG4gICAgKTtcblxuICAgIC8vIENyZWF0ZSBhcnRpZmFjdCBidWNrZXQgZm9yIHBpcGVsaW5lXG4gICAgY29uc3QgYXJ0aWZhY3RCdWNrZXQgPSBuZXcgczMuQnVja2V0KHRoaXMsICdQaXBlbGluZUFydGlmYWN0cycsIHtcbiAgICAgIHJlbW92YWxQb2xpY3k6IGNkay5SZW1vdmFsUG9saWN5LkRFU1RST1ksXG4gICAgICBhdXRvRGVsZXRlT2JqZWN0czogdHJ1ZSxcbiAgICB9KTtcblxuICAgIC8vIENvZGVQaXBlbGluZVxuICAgIGNvbnN0IHNvdXJjZU91dHB1dCA9IG5ldyBjb2RlcGlwZWxpbmUuQXJ0aWZhY3QoKTtcbiAgICBjb25zdCBidWlsZE91dHB1dCA9IG5ldyBjb2RlcGlwZWxpbmUuQXJ0aWZhY3QoKTtcblxuICAgIG5ldyBjb2RlcGlwZWxpbmUuUGlwZWxpbmUodGhpcywgJ1BpcGVsaW5lJywge1xuICAgICAgcGlwZWxpbmVOYW1lOiAnQ2FyZEZsdXhQaXBlbGluZScsXG4gICAgICBhcnRpZmFjdEJ1Y2tldCxcbiAgICAgIHN0YWdlczogW1xuICAgICAgICB7XG4gICAgICAgICAgc3RhZ2VOYW1lOiAnU291cmNlJyxcbiAgICAgICAgICBhY3Rpb25zOiBbXG4gICAgICAgICAgICBuZXcgY29kZXBpcGVsaW5lX2FjdGlvbnMuUzNTb3VyY2VBY3Rpb24oe1xuICAgICAgICAgICAgICBhY3Rpb25OYW1lOiAnUzNTb3VyY2UnLFxuICAgICAgICAgICAgICBidWNrZXQ6IHByb3BzLmJ1Y2tldCxcbiAgICAgICAgICAgICAgYnVja2V0S2V5OiAndHJpZ2dlci9waXBlbGluZS56aXAnLFxuICAgICAgICAgICAgICBvdXRwdXQ6IHNvdXJjZU91dHB1dCxcbiAgICAgICAgICAgICAgdHJpZ2dlcjogY29kZXBpcGVsaW5lX2FjdGlvbnMuUzNUcmlnZ2VyLkVWRU5UUyxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgIF0sXG4gICAgICAgIH0sXG4gICAgICAgIHtcbiAgICAgICAgICBzdGFnZU5hbWU6ICdCdWlsZCcsXG4gICAgICAgICAgYWN0aW9uczogW1xuICAgICAgICAgICAgbmV3IGNvZGVwaXBlbGluZV9hY3Rpb25zLkNvZGVCdWlsZEFjdGlvbih7XG4gICAgICAgICAgICAgIGFjdGlvbk5hbWU6ICdSdW5QaXBlbGluZScsXG4gICAgICAgICAgICAgIHByb2plY3Q6IGJ1aWxkUHJvamVjdCxcbiAgICAgICAgICAgICAgaW5wdXQ6IHNvdXJjZU91dHB1dCxcbiAgICAgICAgICAgICAgb3V0cHV0czogW2J1aWxkT3V0cHV0XSxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgIF0sXG4gICAgICAgIH0sXG4gICAgICBdLFxuICAgIH0pO1xuICB9XG59XG4iXX0=