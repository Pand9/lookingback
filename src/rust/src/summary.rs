use chrono::{DateTime, Duration, DurationRound, Local, TimeZone};
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use std::{collections::HashMap, fmt::Display};

use crate::{cli::ReportOpts, error::Result, record::AssembledRecord};
pub const MINUTE_FMT: &'static str = "%Y-%m-%d_%H:%M";
pub const DATETIME_MINUTE_FMT: &'static str = "%Y-%m-%d %H:%M";
pub const TIME_MINUTE_FMT: &'static str = "%H:%M";

#[derive(Serialize, Deserialize, PartialEq, Debug)]
pub struct Summary {
    #[serde(
        serialize_with = "serialize_minute",
        deserialize_with = "deserialize_minute"
    )]
    pub from: DateTime<Local>,
    #[serde(
        skip_serializing_if = "Option::is_none",
        serialize_with = "maybe_serialize_minute",
        deserialize_with = "maybe_deserialize_minute"
    )]
    pub to: Option<DateTime<Local>>,
    pub total_ticks: u64,
    pub total_idle_ticks: u64,
    pub untracked_ticks: Option<i64>,
    pub parts: Vec<SummaryPart>,
}

impl Display for Summary {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        let ftotal = (self.total_ticks + self.total_idle_ticks) as f64;
        let percent_tracked = {
            if let Some(untracked) = self.untracked_ticks {
                format!("{:.0}", ftotal / (ftotal + untracked as f64) * 100f64)
            } else {
                "??".to_string()
            }
        };
        write!(
            f,
            "Bucket {}-{} - {}% tracked, of which: {:.0}% busy, {:.0}% idle. Top {} tracked windows:\n",
            self.from.format(DATETIME_MINUTE_FMT),
            self.to.map(|d| d.format(TIME_MINUTE_FMT).to_string()).unwrap_or("...".to_string()),
            percent_tracked,
            self.total_ticks as f64 / ftotal * 100f64,
            self.total_idle_ticks as f64 / ftotal * 100f64,
            self.parts.len()
        )?;
        for (i, part) in self.parts.iter().enumerate() {
            write!(
                f,
                "{:2}: {:.0}% of tracked time - {:.0}% busy, {:.0}% idle -  \"{}\"\n",
                i + 1,
                ((part.ticks + part.idle_ticks) as f64)
                    / (self.total_ticks + self.total_idle_ticks) as f64
                    * 100f64,
                (part.ticks as f64) / (part.ticks + part.idle_ticks) as f64 * 100f64,
                (part.idle_ticks as f64) / (part.ticks + part.idle_ticks) as f64 * 100f64,
                part.tag,
            )?;
        }
        Ok(())
    }
}

#[derive(Serialize, Deserialize, PartialEq, Debug)]
pub struct SummaryPart {
    pub tag: String,
    pub ticks: u64,
    pub idle_ticks: u64,
}

pub fn make_summary(recs: Vec<AssembledRecord>, opts: &ReportOpts) -> Result<Summary> {
    assert!(!recs.is_empty());
    let mut total_ticks = 0;
    let mut total_idle_ticks = 0;
    let (from, to) = if opts.chunk_minutes == 0 {
        (opts.from.clone(), opts.to.clone())
    } else {
        let duration = Duration::minutes(opts.chunk_minutes as i64);
        let from = recs
            .first()
            .unwrap()
            .timestamp
            .duration_trunc(duration)
            .unwrap();
        let opts_to = opts.to.unwrap_or_else(|| Local::now());
        let to = std::cmp::min(opts_to, from + duration);
        (from, Some(to))
    };
    let mut groups: HashMap<String, (u64, u64)> = Default::default();
    for rec in recs {
        let tag = make_tag(&rec);
        let idle = rec.idle_msecs.unwrap_or(0) >= 15000;
        let mut entry = groups.entry(tag.clone()).or_default();
        if idle {
            entry.1 += 1;
            total_idle_ticks += 1;
        } else {
            entry.0 += 1;
            total_ticks += 1;
        }
    }
    let untracked_ticks = if let Some(to) = &to {
        Some(
            to.signed_duration_since(from).num_seconds()
                - total_ticks as i64
                - total_idle_ticks as i64,
        )
    } else {
        None
    };
    let mut groups: Vec<(String, (u64, u64))> = groups.into_iter().collect();
    groups.sort_by_key(|e| -((e.1 .0 + e.1 .1) as i64));
    if opts.chunk_colors != 0 {
        groups.truncate(opts.chunk_colors as usize);
    }
    let parts = groups
        .into_iter()
        .map(|e| SummaryPart {
            tag: e.0,
            ticks: e.1 .0,
            idle_ticks: e.1 .1,
        })
        .collect();
    Ok(Summary {
        from,
        to,
        total_ticks,
        total_idle_ticks,
        untracked_ticks,
        parts,
    })
}

fn make_tag(rec: &AssembledRecord) -> String {
    rec.window_title.clone().unwrap_or("no window".to_owned())
}

fn maybe_deserialize_minute<'de, D>(d: D) -> std::result::Result<Option<DateTime<Local>>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: &str = Deserialize::deserialize(d)?;
    match Local.datetime_from_str(s, MINUTE_FMT) {
        Err(e) => Err(serde::de::Error::custom(format!("chrono error: {}", e))),
        Ok(value) => Ok(Some(value)),
    }
}

fn deserialize_minute<'de, D>(d: D) -> std::result::Result<DateTime<Local>, D::Error>
where
    D: Deserializer<'de>,
{
    let s: &str = Deserialize::deserialize(d)?;
    match Local.datetime_from_str(s, MINUTE_FMT) {
        Err(e) => Err(serde::de::Error::custom(format!("chrono error: {}", e))),
        Ok(value) => Ok(value),
    }
}

fn maybe_serialize_minute<S>(
    v: &Option<DateTime<Local>>,
    ser: S,
) -> std::result::Result<S::Ok, S::Error>
where
    S: Serializer,
{
    if let Some(v) = v.as_ref() {
        serialize_minute(v, ser)
    } else {
        ser.serialize_none()
    }
}

fn serialize_minute<S>(v: &DateTime<Local>, ser: S) -> std::result::Result<S::Ok, S::Error>
where
    S: Serializer,
{
    let s = v.format(MINUTE_FMT).to_string();
    ser.serialize_str(&s)
}
