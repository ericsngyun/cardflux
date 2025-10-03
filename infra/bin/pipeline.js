#!/usr/bin/env node
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
require("source-map-support/register");
const cdk = __importStar(require("aws-cdk-lib"));
const storage_stack_1 = require("../lib/storage-stack");
const cdn_stack_1 = require("../lib/cdn-stack");
const pipeline_stack_1 = require("../lib/pipeline-stack");
const app = new cdk.App();
const env = {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
};
const storageStack = new storage_stack_1.StorageStack(app, 'CardFluxStorageStack', { env });
const cdnStack = new cdn_stack_1.CdnStack(app, 'CardFluxCdnStack', {
    env,
    bucket: storageStack.bucket,
});
new pipeline_stack_1.PipelineStack(app, 'CardFluxPipelineStack', {
    env,
    bucket: storageStack.bucket,
});
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoicGlwZWxpbmUuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyJwaXBlbGluZS50cyJdLCJuYW1lcyI6W10sIm1hcHBpbmdzIjoiOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFDQSx1Q0FBcUM7QUFDckMsaURBQW1DO0FBQ25DLHdEQUFvRDtBQUNwRCxnREFBNEM7QUFDNUMsMERBQXNEO0FBRXRELE1BQU0sR0FBRyxHQUFHLElBQUksR0FBRyxDQUFDLEdBQUcsRUFBRSxDQUFDO0FBRTFCLE1BQU0sR0FBRyxHQUFHO0lBQ1YsT0FBTyxFQUFFLE9BQU8sQ0FBQyxHQUFHLENBQUMsbUJBQW1CO0lBQ3hDLE1BQU0sRUFBRSxPQUFPLENBQUMsR0FBRyxDQUFDLGtCQUFrQixJQUFJLFdBQVc7Q0FDdEQsQ0FBQztBQUVGLE1BQU0sWUFBWSxHQUFHLElBQUksNEJBQVksQ0FBQyxHQUFHLEVBQUUsc0JBQXNCLEVBQUUsRUFBRSxHQUFHLEVBQUUsQ0FBQyxDQUFDO0FBQzVFLE1BQU0sUUFBUSxHQUFHLElBQUksb0JBQVEsQ0FBQyxHQUFHLEVBQUUsa0JBQWtCLEVBQUU7SUFDckQsR0FBRztJQUNILE1BQU0sRUFBRSxZQUFZLENBQUMsTUFBTTtDQUM1QixDQUFDLENBQUM7QUFFSCxJQUFJLDhCQUFhLENBQUMsR0FBRyxFQUFFLHVCQUF1QixFQUFFO0lBQzlDLEdBQUc7SUFDSCxNQUFNLEVBQUUsWUFBWSxDQUFDLE1BQU07Q0FDNUIsQ0FBQyxDQUFDIiwic291cmNlc0NvbnRlbnQiOlsiIyEvdXNyL2Jpbi9lbnYgbm9kZVxuaW1wb3J0ICdzb3VyY2UtbWFwLXN1cHBvcnQvcmVnaXN0ZXInO1xuaW1wb3J0ICogYXMgY2RrIGZyb20gJ2F3cy1jZGstbGliJztcbmltcG9ydCB7IFN0b3JhZ2VTdGFjayB9IGZyb20gJy4uL2xpYi9zdG9yYWdlLXN0YWNrJztcbmltcG9ydCB7IENkblN0YWNrIH0gZnJvbSAnLi4vbGliL2Nkbi1zdGFjayc7XG5pbXBvcnQgeyBQaXBlbGluZVN0YWNrIH0gZnJvbSAnLi4vbGliL3BpcGVsaW5lLXN0YWNrJztcblxuY29uc3QgYXBwID0gbmV3IGNkay5BcHAoKTtcblxuY29uc3QgZW52ID0ge1xuICBhY2NvdW50OiBwcm9jZXNzLmVudi5DREtfREVGQVVMVF9BQ0NPVU5ULFxuICByZWdpb246IHByb2Nlc3MuZW52LkNES19ERUZBVUxUX1JFR0lPTiB8fCAndXMtZWFzdC0xJyxcbn07XG5cbmNvbnN0IHN0b3JhZ2VTdGFjayA9IG5ldyBTdG9yYWdlU3RhY2soYXBwLCAnQ2FyZEZsdXhTdG9yYWdlU3RhY2snLCB7IGVudiB9KTtcbmNvbnN0IGNkblN0YWNrID0gbmV3IENkblN0YWNrKGFwcCwgJ0NhcmRGbHV4Q2RuU3RhY2snLCB7XG4gIGVudixcbiAgYnVja2V0OiBzdG9yYWdlU3RhY2suYnVja2V0LFxufSk7XG5cbm5ldyBQaXBlbGluZVN0YWNrKGFwcCwgJ0NhcmRGbHV4UGlwZWxpbmVTdGFjaycsIHtcbiAgZW52LFxuICBidWNrZXQ6IHN0b3JhZ2VTdGFjay5idWNrZXQsXG59KTtcbiJdfQ==