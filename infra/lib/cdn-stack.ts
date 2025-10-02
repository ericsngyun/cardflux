import * as cdk from 'aws-cdk-lib';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export interface CdnStackProps extends cdk.StackProps {
  bucket: s3.Bucket;
}

export class CdnStack extends cdk.Stack {
  public readonly distribution: cloudfront.Distribution;

  constructor(scope: Construct, id: string, props: CdnStackProps) {
    super(scope, id, props);

    // Create CloudFront distribution
    this.distribution = new cloudfront.Distribution(this, 'CardFluxDistribution', {
      defaultBehavior: {
        origin: new origins.S3Origin(props.bucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: new cloudfront.CachePolicy(this, 'CardFluxCachePolicy', {
          cachePolicyName: 'CardFluxCachePolicy',
          minTtl: cdk.Duration.seconds(1),
          defaultTtl: cdk.Duration.hours(24),
          maxTtl: cdk.Duration.days(365),
          enableAcceptEncodingGzip: true,
          enableAcceptEncodingBrotli: true,
        }),
      },
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      comment: 'CardFlux CDN',
    });

    // Output CloudFront URL
    new cdk.CfnOutput(this, 'DistributionUrl', {
      value: `https://${this.distribution.distributionDomainName}`,
      description: 'CardFlux CDN URL',
    });
  }
}
