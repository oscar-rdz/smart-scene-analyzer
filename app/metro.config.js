// Metro config for the Smart Scene Analyzer Expo app.
//
// Both on-device ML runtimes ship their model as a single opaque binary file
// (`.tflite` for react-native-fast-tflite, `.pte` for react-native-executorch),
// loaded via `require('./assets/models/...')` like an image or a font. Metro
// only bundles extensions it recognizes as assets; anything else it treats as
// a source module and tries (and fails) to parse as JS.
//
// Without the two lines below, `.tflite` and `.pte` are silently dropped from
// the bundle. There is no build error -- the require() resolves at bundle time,
// the app installs, and it fails at *runtime* when the model loader can't find
// the file, pointing at a path that looks completely correct. This is exactly
// the class of failure the artifact contract (CLAUDE.md) warns about: the
// export defines the file, Metro's config decides whether it ships.
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

config.resolver.assetExts.push('tflite', 'pte');

module.exports = config;
