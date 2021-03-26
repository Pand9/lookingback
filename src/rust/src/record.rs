use std::collections::HashMap;

use chrono::{DateTime, Local, TimeZone};
use serde::{Deserialize, Deserializer, Serialize, Serializer};

#[derive(Serialize, Deserialize, Debug)]
pub struct Record {
    #[serde(rename = "type")]
    pub type_: String,
    #[serde(
        default,
        skip_serializing_if = "Option::is_none",
        serialize_with = "serialize_ts",
        deserialize_with = "deserialize_ts"
    )]
    pub timestamp: Option<DateTime<Local>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub idle_msecs: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "window ID")]
    pub window_id: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none", rename = "window title")]
    pub window_title: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub windows: Option<Vec<HashMap<String, String>>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub desktops: Option<Vec<HashMap<String, String>>>,
}

pub const FMT: &'static str = "%Y-%m-%d_%H:%M:%S.%.3f";
pub const PARSE_FMT: &'static str = "%Y-%m-%d_%H:%M:%S.%f";

pub fn serialize_ts<S>(v: &Option<DateTime<Local>>, ser: S) -> Result<S::Ok, S::Error>
where
    S: Serializer,
{
    if let Some(v) = v.as_ref() {
        let s = v.format(FMT).to_string();
        ser.serialize_str(&s)
    } else {
        ser.serialize_none()
    }
}

pub fn deserialize_ts<'de, D>(d: D) -> Result<Option<DateTime<Local>>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: &str = Deserialize::deserialize(d)?;
    match Local.datetime_from_str(s, PARSE_FMT) {
        Err(e) => Err(serde::de::Error::custom(format!("chrono error: {}", e))),
        Ok(value) => Ok(Some(value)),
    }
}
