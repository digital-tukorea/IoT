package com.omni.smart.receiver;

import android.Manifest;
import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;

import androidx.core.app.ActivityCompat;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;

import com.omni.smart.R;
import com.omni.smart.activity.MainActivity;
import com.omni.smart.model.Clothing;
import com.omni.smart.repository.ClothingRepository;

import java.util.Calendar;
import java.util.List;

public class LaundryAlarmReceiver extends BroadcastReceiver {

    private static final String CHANNEL_ID = "laundry_channel";
    private static final int NOTIFICATION_ID = 2001;
    private static final int ALARM_REQUEST_CODE = 3001;

    @Override
    public void onReceive(Context context, Intent intent) {
        final PendingResult pendingResult = goAsync();

        ClothingRepository repository = new ClothingRepository();
        repository.getClothesOnce(clothes -> {
            try {
                if (clothes != null) {
                    boolean hasLaundry = false;
                    for (Clothing c : clothes) {
                        if (c.isNeedsLaundry()) {
                            hasLaundry = true;
                            break;
                        }
                    }
                    if (hasLaundry) {
                        showNotification(context);
                    }
                }
            } finally {
                scheduleNext(context);
                pendingResult.finish();
            }
        });
    }

    private void showNotification(Context context) {
        if (ActivityCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED) {
            android.util.Log.w("LaundryAlarmReceiver", "POST_NOTIFICATIONS permission not granted, skip notify");
            return;
        }

        createChannelIfNeeded(context);

        Intent mainIntent = new Intent(context, MainActivity.class);
        PendingIntent contentIntent = PendingIntent.getActivity(
                context, 0, mainIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification notification = new NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(R.mipmap.ic_launcher)
                .setContentTitle("빨래할 시간이에요 🧺")
                .setContentText("일주일 이상 입지 않은 옷이 있어요. 빨래를 해보세요!")
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .setContentIntent(contentIntent)
                .build();

        NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, notification);
    }

    private void createChannelIfNeeded(Context context) {
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "빨래 알림", NotificationManager.IMPORTANCE_HIGH); // DEFAULT → HIGH
        channel.setDescription("일주일 이상 안 입은 옷이 있을 때 알려줍니다.");
        manager.createNotificationChannel(channel);
    }

    public static void scheduleFirst(Context context) {
        scheduleAt10AM(context, false);
    }

    private static void scheduleNext(Context context) {
        scheduleAt10AM(context, true);
    }

    private static void scheduleAt10AM(Context context, boolean forceNextDay) {
        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarmManager == null) return;

        Calendar calendar = Calendar.getInstance();
        calendar.set(Calendar.HOUR_OF_DAY, 0); // 알림 시각(시): 필요시 여기 숫자 변경
        calendar.set(Calendar.MINUTE, 49);        // 알림 시각(분): 필요시 여기 숫자 변경
        calendar.set(Calendar.SECOND, 0);
        calendar.set(Calendar.MILLISECOND, 0);

        if (forceNextDay || calendar.getTimeInMillis() <= System.currentTimeMillis()) {
            calendar.add(Calendar.DAY_OF_YEAR, 1);
        }

        Intent intent = new Intent(context, LaundryAlarmReceiver.class);
        PendingIntent pendingIntent = PendingIntent.getBroadcast(
                context, ALARM_REQUEST_CODE, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && alarmManager.canScheduleExactAlarms()) {
            alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, calendar.getTimeInMillis(), pendingIntent);
        } else {
            alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, calendar.getTimeInMillis(), pendingIntent);
        }
    }
}