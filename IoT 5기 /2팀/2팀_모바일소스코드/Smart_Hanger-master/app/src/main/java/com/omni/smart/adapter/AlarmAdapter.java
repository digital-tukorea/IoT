package com.omni.smart.adapter;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.view.LayoutInflater;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.omni.smart.databinding.ItemAlarmBinding;
import com.omni.smart.receiver.AlarmReceiver;
import com.omni.smart.util.AlarmStore;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class AlarmAdapter extends RecyclerView.Adapter<AlarmAdapter.VH> {
    private List<AlarmStore.AlarmEntry> alarms = new ArrayList<>();

    public void setAlarms(List<AlarmStore.AlarmEntry> alarms) {
        this.alarms = alarms;
        notifyDataSetChanged();
    }

    @NonNull @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        return new VH(ItemAlarmBinding.inflate(LayoutInflater.from(parent.getContext()), parent, false));
    }

    @Override
    public void onBindViewHolder(@NonNull VH holder, int position) {
        AlarmStore.AlarmEntry entry = alarms.get(position);
        String time = new SimpleDateFormat("HH:mm", Locale.getDefault()).format(new Date(entry.triggerTime));
        holder.binding.tvAlarmLabel.setText(time + " · " + entry.title);

        holder.binding.btnDeleteAlarm.setOnClickListener(v -> {
            Context context = v.getContext();
            Intent intent = new Intent(context, AlarmReceiver.class);
            PendingIntent pi = PendingIntent.getBroadcast(context, entry.requestCode, intent, PendingIntent.FLAG_IMMUTABLE);
            AlarmManager am = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            if (am != null) am.cancel(pi);

            AlarmStore.remove(context, entry.requestCode);
            alarms.remove(position);
            notifyItemRemoved(position);
        });
    }

    @Override
    public int getItemCount() { return alarms.size(); }

    static class VH extends RecyclerView.ViewHolder {
        ItemAlarmBinding binding;
        VH(ItemAlarmBinding b) { super(b.getRoot()); binding = b; }
    }
}