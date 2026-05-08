refactor(channel-runtime): migrate artifacts and tasks into runtime server

- Route artifact and task tools through the ChannelRuntimeClient facade
- Expose artifacts, tasks, messages, collaboration, and reactions from __poco_channel_runtime
- Remove old executor injection paths for __poco_channel_tasks and __poco_channel_artifacts
- Cover facade routing and old injector removal with executor unittest cases
- Mark Phase 3 and Phase 4 unified runtime plan criteria complete
