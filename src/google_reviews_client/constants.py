"""Constants for Google Business Profile API endpoints and scopes."""

ACCOUNT_MGMT_BASE = "https://mybusinessaccountmanagement.googleapis.com"
BUSINESS_BASE = "https://mybusiness.googleapis.com/v4"

# required scopes for the Google Business API
SCOPES = [
    "https://www.googleapis.com/auth/business.manage",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

# All fields available on the Location resource (Business Information API v1)
LOCATION_ALL_FIELDS = ",".join([
    "name",
    "languageCode",
    "storeCode",
    "title",
    "phoneNumbers",
    "categories",
    "storefrontAddress",
    "websiteUri",
    "regularHours",
    "specialHours",
    "serviceArea",
    "labels",
    "adWordsLocationExtensions",
    "latlng",
    "openInfo",
    "metadata",
    "profile",
    "relationshipData",
    "moreHours",
    "serviceItems",
])
