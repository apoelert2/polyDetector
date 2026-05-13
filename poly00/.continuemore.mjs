// .continuemore.mjs
export function modifyConfig(config) {
  config.contextProvider = config.contextProvider || {};
  config.contextProvider.maxTokensFromHistory = 8000;
  config.defaultCompletionOptions = config.defaultCompletionOptions || {};
  config.defaultCompletionOptions.maxTokens = 1024;
  config.defaultCompletionOptions.temperature = 0.2;
  return config;
}