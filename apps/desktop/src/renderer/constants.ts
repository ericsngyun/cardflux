/**
 * Application Constants
 *
 * Centralized configuration values for maintainability and clarity.
 * All magic numbers should be defined here with clear documentation.
 */

/**
 * Camera and Detection Constants
 */
export const CAMERA_CONSTANTS = {
  // Image Quality Settings
  CAPTURE_JPEG_QUALITY: 0.98, // High quality (98%) for card identification - preserves fine details
  DETECTION_JPEG_QUALITY: 0.5, // Lower quality (50%) for detection - faster transmission, sufficient for analysis

  // Detection Image Sizing
  DETECTION_WIDTH: 640, // Downsampled width for detection (640x360 @ 16:9)
  BBOX_PADDING: 0.05, // 5% padding around detected card boundary

  // Detection Smoothing & Stabilization
  BBOX_SMOOTHING_ALPHA: 0.3, // Exponential smoothing factor (0.3 = smoother, less jittery)
  STATUS_DEBOUNCE_COUNT: 3, // Require 3 consecutive same statuses before updating
  STATUS_HISTORY_MAX: 5, // Maximum status history length

  // Auto-Capture Settings
  AUTO_CAPTURE_DELAY_MS: 2000, // Hold card steady for 2 seconds before auto-capture
  AUTO_CAPTURE_UPDATE_INTERVAL_MS: 100, // Update countdown every 100ms

  // Camera Quality Preferences
  CAMERA_IDEAL_WIDTH: 1920,
  CAMERA_IDEAL_HEIGHT: 1080,
  CAMERA_MIN_WIDTH: 1280,
  CAMERA_MIN_HEIGHT: 720,
  CAMERA_IDEAL_FPS: 30,
  CAMERA_MIN_FPS: 15,
  CAMERA_IDEAL_FOCUS_DISTANCE: 0.3, // 30cm - ideal for card scanning
  CAMERA_IDEAL_ZOOM: 1.2, // Slight zoom helps focus on close objects
} as const;

/**
 * Detection Polling Intervals
 */
export const POLL_INTERVALS = {
  ACTIVE: 500, // 500ms when card detected and positioning (2 FPS)
  IDLE: 1000, // 1000ms when no card detected (1 FPS) - saves battery
  BACKGROUND: 2000, // 2000ms when app backgrounded (0.5 FPS) - minimal checking
  VIDEO_READY_CHECK: 100, // Check video ready state every 100ms during initialization
} as const;

/**
 * Application Settings
 */
export const APP_CONSTANTS = {
  // Duplicate Detection
  DUPLICATE_DETECTION_WINDOW_MS: 30000, // 30 seconds - consider card duplicate if scanned within this window

  // Notification Display
  NOTIFICATION_DURATION_MS: 5000, // 5 seconds - auto-dismiss notifications

  // Multi-Frame Capture
  MULTI_FRAME_CAPTURE_COUNT: 3, // Capture 3 frames for multi-frame fusion
  MULTI_FRAME_CAPTURE_DELAY_MS: 200, // 200ms between frame captures

  // Settings Persistence
  SETTINGS_STORAGE_KEY: 'cardflux-settings',
  SETTINGS_SAVE_DEBOUNCE_MS: 500, // Wait 500ms after last change before saving

  // Card Stack Export
  EXPORT_FILENAME_PREFIX: 'cardflux-export',
  EXPORT_DATE_FORMAT: 'YYYY-MM-DD_HHmmss',
} as const;

/**
 * Rate Limiting Configuration
 */
export const RATE_LIMITS = {
  // Identification: Max 10 requests per 10 seconds (~1s per card average)
  IDENTIFY: {
    maxRequests: 10,
    windowMs: 10000,
    message: 'Too many identification requests. Please wait a moment.',
  },

  // Detection: Max 30 requests per 10 seconds (supports 2 FPS active polling)
  DETECT: {
    maxRequests: 30,
    windowMs: 10000,
    message: 'Detection rate limit exceeded. Slow down scanning.',
  },

  // Camera Capture: Max 20 captures per 10 seconds (prevents SPACE key spam)
  CAPTURE: {
    maxRequests: 20,
    windowMs: 10000,
    message: 'Too many capture requests. Please wait a moment.',
  },

  // Data Sync: Max 1 request per 60 seconds (expensive operation)
  SYNC: {
    maxRequests: 1,
    windowMs: 60000,
    message: 'Data sync already in progress. Please wait before syncing again.',
  },
} as const;

/**
 * Python Service Configuration
 */
export const PYTHON_SERVICE = {
  // Timeouts
  INITIALIZE_TIMEOUT_MS: 60000, // 60 seconds for initialization (loads ML models)
  IDENTIFY_TIMEOUT_MS: 20000, // 20 seconds for identification
  DETECT_TIMEOUT_MS: 5000, // 5 seconds for detection (should be fast)

  // Process Management
  GRACEFUL_SHUTDOWN_TIMEOUT_MS: 5000, // Wait 5s for SIGTERM before SIGKILL
  ZOMBIE_CHECK_DELAY_MS: 2000, // Wait 2s after SIGKILL to verify termination
  ABSOLUTE_STOP_TIMEOUT_MS: 10000, // Force resolve after 10s no matter what

  // Request Configuration
  DEFAULT_TOP_K: 50, // Return top 50 matches for re-ranking
  MAX_MULTI_FRAME_IMAGES: 10, // Maximum frames for multi-frame identification
} as const;

/**
 * File Size Limits
 */
export const FILE_LIMITS = {
  // Image Upload Limits
  MAX_IMAGE_SIZE_BYTES: 10 * 1024 * 1024, // 10 MB actual image data
  MAX_BASE64_SIZE_BYTES: 14 * 1024 * 1024, // ~14 MB base64 (accounts for 33% overhead)

  // Sync Timeout
  SYNC_TIMEOUT_MS: 10 * 60 * 1000, // 10 minutes for large dataset sync
} as const;

/**
 * UI Constants
 */
export const UI_CONSTANTS = {
  // Card Stack
  CARD_STACK_MAX_VISIBLE: 100, // Virtual scrolling kicks in after 100 cards

  // Animation Timings
  NOTIFICATION_FADE_MS: 300,
  MODAL_TRANSITION_MS: 200,

  // Detection Overlay
  OVERLAY_CORNER_SIZE_PX: 20,
  OVERLAY_LINE_WIDTH_PX: 3,

  // Colors
  COLORS: {
    SUCCESS: '#4CAF50', // Green
    WARNING: '#FFC107', // Yellow
    ERROR: '#F44336', // Red
    INFO: '#2196F3', // Blue
  },
} as const;

/**
 * Type exports for type safety
 */
export type DetectionStatus =
  | 'no_card'
  | 'card_detected'
  | 'card_too_far'
  | 'card_too_close'
  | 'card_angled'
  | 'card_ready'
  | 'poor_lighting'
  | 'too_blurry'
  | 'glare_detected';

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export type ConfidenceLevel = 'HIGH' | 'MODERATE' | 'LOW';
