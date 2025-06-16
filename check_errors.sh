#!/bin/bash

echo "檢查最近的錯誤..."

# 查看最近的錯誤日誌
gcloud logging read 'resource.type="cloud_run_revision" 
AND resource.labels.service_name="frequency-bot" 
AND (severity="ERROR" OR textPayload:"ERROR" OR textPayload:"Exception")' \
--limit=10 \
--format="table(timestamp,textPayload)" \
--project=probable-axon-451311-e1

echo ""
echo "查看詳細錯誤堆疊..."
gcloud logging read 'resource.type="cloud_run_revision" 
AND resource.labels.service_name="frequency-bot" 
AND textPayload:"Traceback"' \
--limit=5 \
--format="value(textPayload)" \
--project=probable-axon-451311-e1