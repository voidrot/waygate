# Changelog

## [0.1.1](https://github.com/voidrot/waygate/compare/waygate-core-v0.1.0...waygate-core-v0.1.1) (2026-04-23)


### Features

* **api:** add agent-session webhook triggers ([252cd41](https://github.com/voidrot/waygate/commit/252cd417fdd933761645842e64b13b9180c70626))
* **core:** add communication client plugin foundation ([78a1263](https://github.com/voidrot/waygate/commit/78a1263611909a060121fd6d41b71c8265d7e4a3))
* **core:** add LLM provider readiness hooks ([aac37aa](https://github.com/voidrot/waygate/commit/aac37aad8320a1eb65795b31b72731bc30931fb7))
* **core:** add migration metadata discovery ([ba2e672](https://github.com/voidrot/waygate/commit/ba2e672e0250cf8fdfd7e07d02a19fa207c5668f))
* **core:** add plugin public API, storage namespaces, and app context ([82e998a](https://github.com/voidrot/waygate/commit/82e998a9f85c7cc7f6adf3286c39d6cb09df3d8d))
* **core:** add plugin public API, storage namespaces, and app context accessor ([d719b5d](https://github.com/voidrot/waygate/commit/d719b5dac20e572eb5fec96ed2db564305363c6c))
* **core:** add raw document content typing ([f4700a2](https://github.com/voidrot/waygate/commit/f4700a2dd674900d258fbe527472fd6f10e14622))
* **core:** add relational document index schema ([eb48f8e](https://github.com/voidrot/waygate/commit/eb48f8e141480cf0f4cdfff0dd7054c456a6552a))
* **core:** add typed document artifact contracts ([121ad21](https://github.com/voidrot/waygate/commit/121ad21570eb37109edaf1d812c7f98ebadd44a0))
* **llm:** implement LLM workflow profiles and options resolution ([39ffd83](https://github.com/voidrot/waygate/commit/39ffd8342de2b71da50eb2ccd73308cdfdbac383))
* **templates:** add support for custom document templates and environment configuration ([b918708](https://github.com/voidrot/waygate/commit/b918708351f0b311e2b78ddc719d4488e668a85f))
* **tests:** add get_plugins_for_hook method to fake_manager in test_bootstrap ([c863b4a](https://github.com/voidrot/waygate/commit/c863b4ae40bd6995034bf9d661388553a5d2e297))
* **web:** add unified web app and shared ingress ([074d2cb](https://github.com/voidrot/waygate/commit/074d2cb4d37cd136b174d9eeab34c28129c75a5d))
* **worker:** add transport-agnostic worker runtime ([badfdd5](https://github.com/voidrot/waygate/commit/badfdd5f8669227e8bbe6f2650863bae926a0c64))
* **workflows:** validate targeted llm workflow profiles ([51c9d8f](https://github.com/voidrot/waygate/commit/51c9d8f22016c23f773dced1fd16614bc01a46dc))


### Bug Fixes

* **core:** cache app context across bootstrap calls ([de60868](https://github.com/voidrot/waygate/commit/de608688ccdcef29e2580bb03d026fff907f1b57))
* **core:** ensure global app context is initialized correctly ([3fa30dd](https://github.com/voidrot/waygate/commit/3fa30ddb4d7faaf3571d168ae2a671b463762600))
* **core:** ignore external tables in alembic ([971c01b](https://github.com/voidrot/waygate/commit/971c01b698d9c186d4a77b3e8ed4afb245b02c7f))
* **plugins:** restore provider and storage contracts ([4e65931](https://github.com/voidrot/waygate/commit/4e65931e540a6950453efe7b962cd0653cdf9569))


### Documentation

* **readme:** document env-backed package config ([5561d82](https://github.com/voidrot/waygate/commit/5561d825241865718b105882b6697ca97a10e38b))
* update docs across the project ([818c745](https://github.com/voidrot/waygate/commit/818c7454baf3c5a41f921a6c24aaaf41e136639c))
