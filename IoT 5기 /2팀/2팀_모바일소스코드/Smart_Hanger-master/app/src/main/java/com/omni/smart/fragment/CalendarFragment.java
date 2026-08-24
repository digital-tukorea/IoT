package com.omni.smart.fragment;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;

import com.omni.smart.adapter.AlarmAdapter;
import com.omni.smart.adapter.CalendarDayAdapter;
import com.omni.smart.adapter.EventAdapter;
import com.omni.smart.databinding.FragmentCalendarBinding;
import com.omni.smart.helper.PermissionHelper;
import com.omni.smart.model.CalendarEvent;
import com.omni.smart.util.AlarmStore;
import com.omni.smart.util.CalendarHelper;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public class CalendarFragment extends Fragment {
    private FragmentCalendarBinding binding;
    private EventAdapter eventAdapter;
    private AlarmAdapter alarmAdapter;
    private CalendarDayAdapter dayAdapter;

    private final Calendar visibleMonth = Calendar.getInstance(); // 지금 보고 있는 달
    private final Calendar selectedDay = Calendar.getInstance();  // 선택된 날짜

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        binding = FragmentCalendarBinding.inflate(inflater, container, false);
        return binding.getRoot();
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);

        eventAdapter = new EventAdapter();
        eventAdapter.setOnAlarmSetListener((event, triggerTime) -> loadAlarms());
        binding.rvEvents2.setLayoutManager(new LinearLayoutManager(getContext()));
        binding.rvEvents2.setAdapter(eventAdapter);

        alarmAdapter = new AlarmAdapter();
        binding.rvAlarms.setLayoutManager(new LinearLayoutManager(getContext()));
        binding.rvAlarms.setAdapter(alarmAdapter);

        dayAdapter = new CalendarDayAdapter(day -> {
            selectedDay.set(visibleMonth.get(Calendar.YEAR), visibleMonth.get(Calendar.MONTH), day);
            renderMonthGrid();
            loadEventsForSelectedDay();
        });
        binding.rvCalendarDays.setAdapter(dayAdapter);

        binding.btnPrevMonth.setOnClickListener(v -> {
            visibleMonth.add(Calendar.MONTH, -1);
            renderMonthGrid();
        });
        binding.btnNextMonth.setOnClickListener(v -> {
            visibleMonth.add(Calendar.MONTH, 1);
            renderMonthGrid();
        });

        // 더 이상 폰 캘린더 앱을 열지 않음 — 새로고침 버튼으로 재사용
        binding.btnAddEvent2.setOnClickListener(v -> refreshAll());

        binding.swipeRefreshCalendar.setOnRefreshListener(() -> {
            refreshAll();
            binding.swipeRefreshCalendar.setRefreshing(false);
        });

        refreshAll();
    }

    private void refreshAll() {
        renderMonthGrid();
        loadEventsForSelectedDay();
        loadAlarms();
    }

    private void renderMonthGrid() {
        int year = visibleMonth.get(Calendar.YEAR);
        int month = visibleMonth.get(Calendar.MONTH);

        binding.tvMonthLabel.setText(year + "년 " + (month + 1) + "월");

        List<Integer> days = new ArrayList<>();
        Calendar cal = (Calendar) visibleMonth.clone();
        cal.set(Calendar.DAY_OF_MONTH, 1);
        int firstWeekday = cal.get(Calendar.DAY_OF_WEEK); // 1=일요일
        int daysInMonth = cal.getActualMaximum(Calendar.DAY_OF_MONTH);

        for (int i = 1; i < firstWeekday; i++) days.add(0);
        for (int d = 1; d <= daysInMonth; d++) days.add(d);

        Set<Integer> eventDays = PermissionHelper.hasPermissions(requireContext())
                ? CalendarHelper.getEventDaysInMonth(requireContext(), year, month)
                : new HashSet<>();

        int today = -1;
        Calendar now = Calendar.getInstance();
        if (now.get(Calendar.YEAR) == year && now.get(Calendar.MONTH) == month) {
            today = now.get(Calendar.DAY_OF_MONTH);
        }

        int selected = (selectedDay.get(Calendar.YEAR) == year && selectedDay.get(Calendar.MONTH) == month)
                ? selectedDay.get(Calendar.DAY_OF_MONTH) : -1;

        dayAdapter.submit(days, eventDays, selected, today);
    }

    private void loadEventsForSelectedDay() {
        SimpleDateFormat sdf = new SimpleDateFormat("M월 d일 일정", Locale.getDefault());
        binding.tvSelectedDayLabel.setText(sdf.format(selectedDay.getTime()));

        if (PermissionHelper.hasPermissions(requireContext())) {
            List<CalendarEvent> events = CalendarHelper.getEventsForDate(requireContext(), selectedDay);
            eventAdapter.setEventList(events);
            boolean empty = events == null || events.isEmpty();
            binding.rvEvents2.setVisibility(empty ? View.GONE : View.VISIBLE);
            binding.layoutEmptyEvents.setVisibility(empty ? View.VISIBLE : View.GONE);
        } else {
            binding.rvEvents2.setVisibility(View.GONE);
            binding.layoutEmptyEvents.setVisibility(View.VISIBLE);
        }
    }

    private void loadAlarms() {
        List<AlarmStore.AlarmEntry> alarms = AlarmStore.getAll(requireContext());
        alarmAdapter.setAlarms(alarms);
        boolean empty = alarms.isEmpty();
        binding.rvAlarms.setVisibility(empty ? View.GONE : View.VISIBLE);
        binding.tvNoAlarms.setVisibility(empty ? View.VISIBLE : View.GONE);
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        binding = null;
    }
}