# CHANGELOG

<!-- version list -->

## v0.2.0 (2025-12-12)

### Chores

- **ci**: Add workflow_dispatch trigger for manual CI runs
  ([`85fff58`](https://github.com/apathetic-tools/serger/commit/85fff58747e5ad4ce034f6992522dbbc9c8b055b))

- **deps**: Bump actions/checkout from 5 to 6
  ([#2](https://github.com/apathetic-tools/serger/pull/2),
  [`4ea9b4b`](https://github.com/apathetic-tools/serger/commit/4ea9b4bce3d3de2980c95e5bf1af2a94fc4fbe0f))

- **dev**: Add quiet modes to suppress success messages
  ([`63f96b0`](https://github.com/apathetic-tools/serger/commit/63f96b0ac054f6710c90764b7b47531094e64f4c))

- **pytest**: Suppress pytest-benchmark warnings in parallel tests
  ([`53b54c9`](https://github.com/apathetic-tools/serger/commit/53b54c9a9916204242a8aa025675c811482637b6))

### Features

- **stitch**: Improve module collection and shim generation with enhanced testing
  ([`a08e4c4`](https://github.com/apathetic-tools/serger/commit/a08e4c48ec6e392e866804805f4e420c9b87845a))

### Refactoring

- **build**: Rename build tool detection constants and config settings
  ([`31f3439`](https://github.com/apathetic-tools/serger/commit/31f3439cc57d7d263ae68e362ad5417121dda911))

- **logs**: Unify logging API and improve logger configuration
  ([`579b02a`](https://github.com/apathetic-tools/serger/commit/579b02ac38651cfb140185de611deb8e10f1ce03))

- **test**: Use apathetic_utils.load_toml instead of manual tomllib import
  ([`ae6e9f7`](https://github.com/apathetic-tools/serger/commit/ae6e9f7e31359426c6438a5b8a1e0ed2c1cdf289))

- **tests**: Require tmp_path parameter in build_final_script utilities
  ([`d3a093f`](https://github.com/apathetic-tools/serger/commit/d3a093fdb9886a5b0d52f09d319677b6ede6ebd5))

### Testing

- **log-level**: Improve trace message assertions in verbose flag test
  ([`1683cde`](https://github.com/apathetic-tools/serger/commit/1683cde81b778da537c2ade1e45ec690931a8635))

- **tests**: Migrate additional test files to tmp_path fixture
  ([`4f66eca`](https://github.com/apathetic-tools/serger/commit/4f66eca6f965f36a3e848322a5cf4132c92f0385))

- **tests**: Migrate remaining integration tests to tmp_path
  ([`7a78b4c`](https://github.com/apathetic-tools/serger/commit/7a78b4c33ceae4c3146ce05eacf715b9aee739e7))

- **tests**: Migrate remaining tests in test_stitch_modules to tmp_path
  ([`532bc9a`](https://github.com/apathetic-tools/serger/commit/532bc9aa6dbca9b000b8904dda9c607f75944e10))

- **tests**: Migrate test_build_tool_command and test_post_stitch_processing to tmp_path
  ([`9ac2cea`](https://github.com/apathetic-tools/serger/commit/9ac2ceaaee4c3c446cf1645add7ec7271d1559da))

- **tests**: Migrate test_execute_post_processing to tmp_path
  ([`24422a0`](https://github.com/apathetic-tools/serger/commit/24422a056685948e75097332d0c7a6e80393a996))

- **tests**: Migrate test_extract_pyproject_metadata to tmp_path
  ([`a823938`](https://github.com/apathetic-tools/serger/commit/a8239381c35e0a4a508c6ad8e30a07cdef2ce629))

- **tests**: Migrate test_priv__collect_modules and test_compute_module_order to tmp_path
  ([`9aff99c`](https://github.com/apathetic-tools/serger/commit/9aff99c3569afe5f3c0648f09f3b3479e60f2a76))

- **tests**: Migrate tests to tmp_path fixture
  ([`f74fb89`](https://github.com/apathetic-tools/serger/commit/f74fb892fef2ea0a81abf5f437f596225a339f08))


## v0.1.0 (2025-11-29)

- Initial Release
