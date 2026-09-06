# DEMO/SAMPLE Legal Knowledge Base

本目录是 **DEMO/SAMPLE 演示知识库**，不是真实法律法规库。

每条记录都带 `is_demo_sample: true`、`DEMO/SAMPLE` 来源标识和无效示例 URL，
防止系统或演示者把示例内容误认为真实法条。

企业级实现中，该目录应由人工/经核验的数据管线替换，并在保留
`document_id`、`source_url`、`issuing_authority`、`effective_date`、`domain`、
`version`、`status`、`jurisdiction`、`source_type`、`updated_at` 元数据后进入向量库。

检索层支持 status/legal_domain/jurisdiction/source_type/有效期过滤；
当前 demo 记录均为 `status=effective` 的 `demo_sample`，不代表真实法规。
