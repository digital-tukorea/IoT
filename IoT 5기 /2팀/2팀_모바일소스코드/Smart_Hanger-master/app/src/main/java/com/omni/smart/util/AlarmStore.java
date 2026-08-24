package com.omni.smart.util;

import android.content.Context;
import android.content.SharedPreferences;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.util.ArrayList;
import java.util.List;

public class AlarmStore {
    private static final String PREF = "alarm_store";
    private static final String KEY = "alarms";

    public static class AlarmEntry {
        public int requestCode;
        public String title;
        public long triggerTime;

        public AlarmEntry(int requestCode, String title, long triggerTime) {
            this.requestCode = requestCode;
            this.title = title;
            this.triggerTime = triggerTime;
        }
    }

    public static int buildRequestCode(long startTime, String title) {
        return (int) (startTime ^ (title == null ? 0 : title.hashCode()));
    }

    public static void save(Context context, AlarmEntry entry) {
        List<AlarmEntry> list = getAll(context);
        list.removeIf(e -> e.requestCode == entry.requestCode);
        list.add(entry);
        write(context, list);
    }

    public static void remove(Context context, int requestCode) {
        List<AlarmEntry> list = getAll(context);
        list.removeIf(e -> e.requestCode == requestCode);
        write(context, list);
    }

    public static List<AlarmEntry> getAll(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREF, Context.MODE_PRIVATE);
        String json = prefs.getString(KEY, null);
        if (json == null) return new ArrayList<>();
        AlarmEntry[] arr = new Gson().fromJson(json, AlarmEntry[].class);
        List<AlarmEntry> list = new ArrayList<>();
        if (arr != null) for (AlarmEntry e : arr) list.add(e);
        return list;
    }

    private static void write(Context context, List<AlarmEntry> list) {
        SharedPreferences prefs = context.getSharedPreferences(PREF, Context.MODE_PRIVATE);
        prefs.edit().putString(KEY, new Gson().toJson(list)).apply();
    }
}