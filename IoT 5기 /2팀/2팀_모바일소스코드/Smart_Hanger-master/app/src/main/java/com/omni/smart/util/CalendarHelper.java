package com.omni.smart.util;

import android.content.ContentResolver;
import android.content.Context;
import android.database.Cursor;
import android.provider.CalendarContract;

import com.omni.smart.model.CalendarEvent;

import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;

public class CalendarHelper {
    public static List<CalendarEvent> getTodayEvents(Context context) {
        List<CalendarEvent> events = new ArrayList<>();
        ContentResolver contentResolver = context.getContentResolver();

        Calendar beginTime = Calendar.getInstance();
        beginTime.set(Calendar.HOUR_OF_DAY, 0);
        beginTime.set(Calendar.MINUTE, 0);
        beginTime.set(Calendar.SECOND, 0);

        Calendar endTime = Calendar.getInstance();
        endTime.set(Calendar.HOUR_OF_DAY, 23);
        endTime.set(Calendar.MINUTE, 59);
        endTime.set(Calendar.SECOND, 59);

        // all-day 일정은 DTSTART가 UTC 자정 기준으로 저장되므로 로컬 범위만으로는
        // 못 잡을 수 있음 (getEventsForDate()엔 이미 있던 보정을 여기도 추가함).
        Calendar utcBegin = Calendar.getInstance();
        utcBegin.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
        utcBegin.set(Calendar.HOUR_OF_DAY, 0);
        utcBegin.set(Calendar.MINUTE, 0);
        utcBegin.set(Calendar.SECOND, 0);
        utcBegin.set(Calendar.MILLISECOND, 0);
        long utcDayStart = utcBegin.getTimeInMillis();
        long utcDayEnd = utcDayStart + 24 * 60 * 60 * 1000L;

        String[] projection = new String[]{
                CalendarContract.Events.TITLE,
                CalendarContract.Events.DTSTART,
                CalendarContract.Events.DTEND,
                CalendarContract.Events.EVENT_LOCATION
        };

        String selection = "(" + CalendarContract.Events.DTSTART + " >= ? AND " + CalendarContract.Events.DTSTART + " <= ?)"
                + " OR (" + CalendarContract.Events.ALL_DAY + " = 1 AND "
                + CalendarContract.Events.DTSTART + " >= ? AND " + CalendarContract.Events.DTSTART + " < ?)";
        String[] selectionArgs = new String[]{
                String.valueOf(beginTime.getTimeInMillis()),
                String.valueOf(endTime.getTimeInMillis()),
                String.valueOf(utcDayStart),
                String.valueOf(utcDayEnd)
        };

        try (Cursor cursor = contentResolver.query(
                CalendarContract.Events.CONTENT_URI,
                projection,
                selection,
                selectionArgs,
                CalendarContract.Events.DTSTART + " ASC"
        )) {
            if (cursor != null && cursor.moveToFirst()) {
                do {
                    String title = cursor.getString(0);
                    long start = cursor.getLong(1);
                    long end = cursor.getLong(2);
                    String location = cursor.getString(3);
                    events.add(new CalendarEvent(title, start, end, location));
                } while (cursor.moveToNext());
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        return events;
    }

    /**
     * Additive method: 한 달치 날짜 중 일정이 있는 날짜(1~31)만 뽑아서 반환.
     * 월 달력 격자에 점(dot) 표시할 때 씀. 기존 메서드들은 그대로 둠.
     */
    public static java.util.Set<Integer> getEventDaysInMonth(Context context, int year, int month) {
        java.util.Set<Integer> days = new java.util.HashSet<>();

        Calendar start = Calendar.getInstance();
        start.set(year, month, 1, 0, 0, 0);
        Calendar end = (Calendar) start.clone();
        end.add(Calendar.MONTH, 1);
        end.add(Calendar.MILLISECOND, -1);

        String[] projection = new String[]{CalendarContract.Events.DTSTART};
        String selection = CalendarContract.Events.DTSTART + " >= ? AND " + CalendarContract.Events.DTSTART + " <= ?";
        String[] selectionArgs = new String[]{
                String.valueOf(start.getTimeInMillis()),
                String.valueOf(end.getTimeInMillis())
        };

        try (Cursor cursor = context.getContentResolver().query(
                CalendarContract.Events.CONTENT_URI, projection, selection, selectionArgs, null)) {
            if (cursor != null && cursor.moveToFirst()) {
                Calendar c = Calendar.getInstance();
                do {
                    c.setTimeInMillis(cursor.getLong(0));
                    days.add(c.get(Calendar.DAY_OF_MONTH));
                } while (cursor.moveToNext());
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        return days;
    }

    /**
     * Additive method: 특정 날짜(day) 하루치 일정만 조회.
     * 월 달력에서 날짜를 눌렀을 때 그 날의 일정을 보여줄 때 씀.
     */
    public static List<CalendarEvent> getEventsForDate(Context context, Calendar day) {
        List<CalendarEvent> events = new ArrayList<>();
        ContentResolver contentResolver = context.getContentResolver();

        Calendar beginTime = (Calendar) day.clone();
        beginTime.set(Calendar.HOUR_OF_DAY, 0);
        beginTime.set(Calendar.MINUTE, 0);
        beginTime.set(Calendar.SECOND, 0);

        Calendar endTime = (Calendar) day.clone();
        endTime.set(Calendar.HOUR_OF_DAY, 23);
        endTime.set(Calendar.MINUTE, 59);
        endTime.set(Calendar.SECOND, 59);

        // all-day 일정은 UTC 자정 기준으로 저장되므로 별도 범위로 한번 더 잡아줌
        Calendar utcBegin = (Calendar) day.clone();
        utcBegin.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
        utcBegin.set(Calendar.HOUR_OF_DAY, 0);
        utcBegin.set(Calendar.MINUTE, 0);
        utcBegin.set(Calendar.SECOND, 0);
        utcBegin.set(Calendar.MILLISECOND, 0);
        long utcDayStart = utcBegin.getTimeInMillis();
        long utcDayEnd = utcDayStart + 24 * 60 * 60 * 1000L;

        String[] projection = new String[]{
                CalendarContract.Events.TITLE,
                CalendarContract.Events.DTSTART,
                CalendarContract.Events.DTEND,
                CalendarContract.Events.EVENT_LOCATION,
                CalendarContract.Events.ALL_DAY
        };

        String selection = "(" + CalendarContract.Events.DTSTART + " >= ? AND " + CalendarContract.Events.DTSTART + " <= ?)"
                + " OR (" + CalendarContract.Events.ALL_DAY + " = 1 AND "
                + CalendarContract.Events.DTSTART + " >= ? AND " + CalendarContract.Events.DTSTART + " < ?)";
        String[] selectionArgs = new String[]{
                String.valueOf(beginTime.getTimeInMillis()),
                String.valueOf(endTime.getTimeInMillis()),
                String.valueOf(utcDayStart),
                String.valueOf(utcDayEnd)
        };

        try (Cursor cursor = contentResolver.query(
                CalendarContract.Events.CONTENT_URI,
                projection,
                selection,
                selectionArgs,
                CalendarContract.Events.DTSTART + " ASC"
        )) {
            if (cursor != null && cursor.moveToFirst()) {
                do {
                    String title = cursor.getString(0);
                    long start = cursor.getLong(1);
                    long end = cursor.getLong(2);
                    String location = cursor.getString(3);
                    events.add(new CalendarEvent(title, start, end, location));
                } while (cursor.moveToNext());
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        return events;
    }
}