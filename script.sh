METADATA_ENDPOINT="http://metadata.google.internal/computeMetadata/v1/instance"

function get_accesstoken() {

curl -s $METADATA_ENDPOINT/service-accounts/default/token -H "Metadata-Flavor: Google" | python -c "import json,sys;obj=json.load(sys.stdin);print(obj['access_token'])"

}

function get_secret() {

curl https://secretmanager.googleapis.com/v1/projects/$1/secrets/$2/versions/latest:access --request "GET" -H "authorization: Bearer $3" -H "content-type: application/json" | python -c "import json,sys;obj=json.load(sys.stdin);print(obj['payload']['data'])" | base64 -d

}

function get_metadata() {

curl $METADATA_ENDPOINT/attributes/$1 -H "Metadata-Flavor: Google" -fsSL

}

PROJECT_ID="$(get_metadata project-id)"

ACCESS_TOKEN="$(get_accesstoken)"

MDP_BDD=$(get_secret $PROJECT_ID $MDP_BDD $ACCESS_TOKEN) 

OPENAI_API_KEY=$(get_secret $PROJECT_ID $OPENAI_API_KEY $ACCESS_TOKEN) 

TELEGRAM_TOKEN=$(get_secret $PROJECT_ID $TELEGRAM_TOKEN $ACCESS_TOKEN) 

unix_socket=$(get_secret $PROJECT_ID $unix_socket $ACCESS_TOKEN) 




