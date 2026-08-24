package com.omni.smart.adapter;

import android.view.LayoutInflater;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.bumptech.glide.Glide;
import com.omni.smart.databinding.ItemForecastBinding;
import com.omni.smart.model.ForecastItem;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

public class ForecastAdapter extends RecyclerView.Adapter<ForecastAdapter.ForecastViewHolder> {
    private List<ForecastItem> forecastList = new ArrayList<>();

    public void setForecastList(List<ForecastItem> list) {
        this.forecastList = list;
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public ForecastViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        ItemForecastBinding binding = ItemForecastBinding.inflate(LayoutInflater.from(parent.getContext()), parent, false);
        return new ForecastViewHolder(binding);
    }

    @Override
    public void onBindViewHolder(@NonNull ForecastViewHolder holder, int position) {
        holder.bind(forecastList.get(position));
    }

    @Override
    public int getItemCount() {
        return forecastList.size();
    }

    static class ForecastViewHolder extends RecyclerView.ViewHolder {
        // dt_txt from OpenWeatherMap is always UTC ("yyyy-MM-dd HH:mm:ss").
        // Parse it as UTC, then re-format in Asia/Seoul so the displayed
        // hour (and therefore day/night icon) matches Korean local time.
        private static final SimpleDateFormat UTC_FORMAT;
        private static final SimpleDateFormat KST_FORMAT;
        static {
            UTC_FORMAT = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault());
            UTC_FORMAT.setTimeZone(TimeZone.getTimeZone("UTC"));
            KST_FORMAT = new SimpleDateFormat("HH:mm", Locale.getDefault());
            KST_FORMAT.setTimeZone(TimeZone.getTimeZone("Asia/Seoul"));
        }

        private ItemForecastBinding binding;

        public ForecastViewHolder(ItemForecastBinding binding) {
            super(binding.getRoot());
            this.binding = binding;
        }

        public void bind(ForecastItem item) {
            String time = item.getDateTime();
            String kstTime = time;
            if (time != null) {
                try {
                    Date utcDate = UTC_FORMAT.parse(time);
                    kstTime = KST_FORMAT.format(utcDate);
                } catch (ParseException e) {
                    // fall back to raw substring if parsing ever fails
                    kstTime = time.length() > 11 ? time.substring(11, 16) : time;
                }
            }
            binding.tvTime.setText(kstTime);
            binding.tvTemp.setText(Math.round(item.getTemp()) + "°C");

            String iconUrl = "https://openweathermap.org/img/wn/" + item.getIcon() + "@2x.png";
            Glide.with(binding.ivWeatherIcon.getContext())
                    .load(iconUrl)
                    .into(binding.ivWeatherIcon);
        }
    }
}