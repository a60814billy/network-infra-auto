# infra-auto

## command reference

### 功能性指令
- `infra-auto sync-config-from-device`: 將設備上的 config 備份至本地的 cfg/ 資料夾中
- `infra-auto apply-cfg-to-device`: 將 cfg/ 資料夾中的 config file 送至設備中替換設備原有的 config
- `infra-auto execute baseline_snmp`: 執行 baseline_snmp 中的程式 (產生 snmp 相關的 configuration，並用 netmiko 送至設備)

### CI pipeline 用的輔助指令
- `infra-auto ci detect-changes`: 透過 GitLab API 或是 git command 找出 cfg 有變動的設備清單
    - 此指令產生的設備清單，可以搭配 `infra-auto sync-config-from-device`, `infra-auto apply-cfg-to-device` 等指令，限縮變動的設備
- `infra-auto ci report-diff-to-mr`: 將指定的檔案內容透過 GitLab API 貼至 Merge Request 中
- `infra-auto ci trigger-sync-from-pipeline`: 在 default branch 上 trigger GitLab pipeline (主要用來做設備設定變更後手動同步用)
- `infra-auto ci run_config`: 讓使用者可以手動觸發 pipeline，指定要在設備中執行的指令，並執行
