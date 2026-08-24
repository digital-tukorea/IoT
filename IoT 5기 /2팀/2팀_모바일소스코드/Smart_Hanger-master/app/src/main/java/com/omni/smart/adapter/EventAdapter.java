package com.omni.smart.adapter;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.ContextWrapper;
import android.content.Intent;
import android.view.LayoutInflater;
import android.view.ViewGroup;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.google.android.material.dialog.MaterialAlertDialogBuilder;
import com.omni.smart.databinding.DialogTimePickerBinding;
import com.omni.smart.databinding.ItemEventBinding;
import com.omni.smart.model.CalendarEvent;
import com.omni.smart.receiver.AlarmReceiver;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class EventAdapter extends RecyclerView.Adapter<EventAdapter.EventViewHolder> {
    private List<CalendarEvent> eventList = new ArrayList<>();

    /**
     * Additive, optional listener. Existing callers that use `new EventAdapter()`
     * (e.g. HomeFragment) never set this, so their behavior is unchanged.
     */
    public interface OnAlarmSetListener {
        void onAlarmSet(CalendarEvent event, long triggerTime);
    }
    private OnAlarmSetListener onAlarmSetListener;
    public void setOnAlarmSetListener(OnAlarmSetListener listener) {
        this.onAlarmSetListener = listener;
    }

    public void setEventList(List<CalendarEvent> list) {
        this.eventList = list;
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public EventViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        ItemEventBinding binding = ItemEventBinding.inflate(LayoutInflater.from(parent.getContext()), parent, false);
        return new EventViewHolder(binding);
    }

    @Override
    public void onBindViewHolder(@NonNull EventViewHolder holder, int position) {
        holder.bind(eventList.get(position));
    }

    @Override
    public int getItemCount() {
        return eventList.size();
    }

    class EventViewHolder extends RecyclerView.ViewHolder {
        private ItemEventBinding binding;

        public EventViewHolder(ItemEventBinding binding) {
            super(binding.getRoot());
            this.binding = binding;
        }

        public void bind(CalendarEvent event) {
            binding.tvEventTitle.setText(event.getTitle());

            SimpleDateFormat sdf = new SimpleDateFormat("HH:mm", Locale.getDefault());
            long durationMs = event.getEndTime() - event.getStartTime();
            String timeStr;
            if (durationMs >= 23 * 60 * 60 * 1000L) {
                timeStr = "하루 종일";
            } else {
                timeStr = sdf.format(new Date(event.getStartTime())) + " - " + sdf.format(new Date(event.getEndTime()));
            }
            binding.tvEventTime.setText(timeStr);

            binding.btnSetAlarm.setOnClickListener(v -> pickAlarmTime(v.getContext(), event));
        }

        /** 날짜는 이미 정해져 있으니(그 일정의 날짜) 시간만 숫자 휠로 골라서 알림 설정 */
        private void pickAlarmTime(Context context, CalendarEvent event) {
            android.app.Activity activity = unwrapActivity(context);
            if (activity == null) return;

            DialogTimePickerBinding dialogBinding = DialogTimePickerBinding.inflate(LayoutInflater.from(activity));

            dialogBinding.npHour.setMinValue(0);
            dialogBinding.npHour.setMaxValue(23);
            dialogBinding.npMinute.setMinValue(0);
            dialogBinding.npMinute.setMaxValue(59);

            Calendar now = Calendar.getInstance();
            dialogBinding.npHour.setValue(now.get(Calendar.HOUR_OF_DAY));
            dialogBinding.npMinute.setValue(now.get(Calendar.MINUTE));

            Calendar eventDay = Calendar.getInstance();
            eventDay.setTimeInMillis(event.getStartTime());

            new MaterialAlertDialogBuilder(activity)
                    .setTitle("알림 시간 설정")
                    .setView(dialogBinding.getRoot())
                    .setPositiveButton("설정", (dialog, which) -> {
                        Calendar triggerCal = (Calendar) eventDay.clone();
                        triggerCal.set(Calendar.HOUR_OF_DAY, dialogBinding.npHour.getValue());
                        triggerCal.set(Calendar.MINUTE, dialogBinding.npMinute.getValue());
                        triggerCal.set(Calendar.SECOND, 0);
                        triggerCal.set(Calendar.MILLISECOND, 0);
                        scheduleAlarm(context, event, triggerCal.getTimeInMillis());
                    })
                    .setNegativeButton("취소", null)
                    .show();
        }

        private void scheduleAlarm(Context context, CalendarEvent event, long triggerTime) {
            if (!com.omni.smart.helper.PermissionHelper.canScheduleExactAlarms(context)) {
                Toast.makeText(context, "정확한 알람 권한이 필요해요. 설정에서 허용해주세요.", Toast.LENGTH_LONG).show();
                android.app.Activity activity = unwrapActivity(context);
                if (activity != null) {
                    com.omni.smart.helper.PermissionHelper.requestExactAlarmPermission(activity);
                }
                return;
            }

            if (triggerTime < System.currentTimeMillis()) {
                Toast.makeText(context, "이미 지난 시각이에요. 다른 시간을 선택해주세요.", Toast.LENGTH_SHORT).show();
                return;
            }

            AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            Intent intent = new Intent(context, AlarmReceiver.class);
            intent.putExtra("EVENT_TITLE", event.getTitle());

            int requestCode = com.omni.smart.util.AlarmStore.buildRequestCode(triggerTime, event.getTitle());
            PendingIntent pendingIntent = PendingIntent.getBroadcast(context, requestCode, intent, PendingIntent.FLAG_IMMUTABLE);

            if (alarmManager != null) {
                alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent);
                com.omni.smart.util.AlarmStore.save(context,
                        new com.omni.smart.util.AlarmStore.AlarmEntry(requestCode, event.getTitle(), triggerTime));
                Toast.makeText(context, "알림이 " + new SimpleDateFormat("M월 d일 HH:mm", Locale.getDefault()).format(new Date(triggerTime)) + "로 설정됐어요", Toast.LENGTH_SHORT).show();
                if (onAlarmSetListener != null) {
                    onAlarmSetListener.onAlarmSet(event, triggerTime);
                }
            }
        }

        private android.app.Activity unwrapActivity(Context context) {
            Context ctx = context;
            while (ctx instanceof ContextWrapper && !(ctx instanceof android.app.Activity)) {
                ctx = ((ContextWrapper) ctx).getBaseContext();
            }
            return ctx instanceof android.app.Activity ? (android.app.Activity) ctx : null;
        }
    }
}