#!/bin/bash
echo '請先執行: gcloud auth login'
echo '認證完成後，此腳本將自動部署'
read -p '按 Enter 繼續部署...'

        gcloud run deploy frequency-bot             --source .             --region=asia-east1             --project=probable-axon-451311-e1             --allow-unauthenticated             --quiet             --format=json
        