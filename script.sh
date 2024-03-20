METADATA_ENDPOINT="http://metadata.google.internal/computeMetadata/v1/instance"

function get_accesstoken() {

curl -s $METADATA_ENDPOINT/service-accounts/default/token -H "Metadata-Flavor: Google" | python -c "import json,sys;obj=json.load(sys.stdin);print(obj['access_token'])"

}

function get_secret() {

curl https://secretmanager.googleapis.com/v1/projects/$1/secrets/$2/versions/latest:access --request "GET" -H "authorization: Bearer $3" -H "content-type: application/json" | python -c "import json,sys;obj=json.load(sys.stdin);print(obj['payload']['data'])" | base64 -d

}

ACCESS_TOKEN="$(get_accesstoken)"

YOUR_SECRET=$(get_secret $PROJECT_ID $SECRET_NAME $ACCESS_TOKEN) 

 PROJECT_ID and SECRET_NAME variables can be taken from instance metadata (once you put them there at instance spawn), with a function like:

function get_metadata() {

curl $METADATA_ENDPOINT/attributes/$1 -H "Metadata-Flavor: Google" -fsSL

}

PROJECT_ID="$(get_metadata project-id)"

SECRET_NAME="$(get_metadata secret-name)" 