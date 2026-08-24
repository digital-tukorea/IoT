package com.omni.smart.adapter;

import android.view.LayoutInflater;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.omni.smart.R;
import com.omni.smart.databinding.ItemCalendarDayBinding;

import java.util.List;
import java.util.Set;

public class CalendarDayAdapter extends RecyclerView.Adapter<CalendarDayAdapter.VH> {

    public interface OnDayClickListener { void onDayClick(int dayOfMonth); }

    private List<Integer> days;      // 0 = 빈칸(이전/다음달), 1~31 = 날짜
    private Set<Integer> eventDays;
    private int selectedDay;
    private int today;
    private final OnDayClickListener listener;

    public CalendarDayAdapter(OnDayClickListener listener) {
        this.listener = listener;
    }

    public void submit(List<Integer> days, Set<Integer> eventDays, int selectedDay, int today) {
        this.days = days;
        this.eventDays = eventDays;
        this.selectedDay = selectedDay;
        this.today = today;
        notifyDataSetChanged();
    }

    @NonNull @Override
    public VH onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        return new VH(ItemCalendarDayBinding.inflate(LayoutInflater.from(parent.getContext()), parent, false));
    }

    @Override
    public void onBindViewHolder(@NonNull VH holder, int position) {
        int day = days.get(position);
        if (day == 0) {
            holder.binding.tvDay.setText("");
            holder.binding.tvDay.setBackground(null);
            holder.binding.dotEvent.setVisibility(android.view.View.GONE);
            holder.itemView.setOnClickListener(null);
            return;
        }

        holder.binding.tvDay.setText(String.valueOf(day));
        holder.binding.dotEvent.setVisibility(eventDays.contains(day) ? android.view.View.VISIBLE : android.view.View.GONE);

        if (day == selectedDay) {
            holder.binding.tvDay.setBackgroundResource(R.drawable.bg_day_selected);
        } else if (day == today) {
            holder.binding.tvDay.setBackgroundResource(R.drawable.bg_day_today);
        } else {
            holder.binding.tvDay.setBackground(null);
        }

        holder.itemView.setOnClickListener(v -> listener.onDayClick(day));
    }

    @Override
    public int getItemCount() { return days == null ? 0 : days.size(); }

    static class VH extends RecyclerView.ViewHolder {
        ItemCalendarDayBinding binding;
        VH(ItemCalendarDayBinding b) { super(b.getRoot()); binding = b; }
    }
}